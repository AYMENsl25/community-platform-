# Talaqi Phase 3 Design

**Status:** Approved for implementation planning

**Date:** 2026-07-28

**Phase:** Events, media, visibility, and venue privacy

**Baseline:** Phase 2 commit `7c13a1aa088a4761b59eaf372edf4f1c978968a0`

## Purpose

Phase 3 turns the existing club, eligibility, discovery, moderation, and audit foundations into the complete event-publishing slice. Eligible members can upload verified images, create club-owned or independent events, publish or duplicate them, manage them from one organizer workspace, and expose safe public details without leaking private-link tokens or exact private venues.

The phase does not implement registration state transitions, capacity reservation, waitlists, attendee management, announcements, notification delivery, online payments, recurring instances, chat, comments, QR check-in, or recommendation ML. Task 3.4 may render an explicit attendee placeholder, but Phase 4 owns attendee data and operations.

## Approved product decisions

- Only an active, email-verified member with a complete profile and current organizer/community-rules acceptance may create events or media intended for organizer content.
- An event is owned by exactly one club or one independent owner. Club owners and admins may manage club events. Independent events are managed only by their owner.
- A new account may own at most three active independent events unless the configured regional trust limit is higher. Reducing a limit does not delete existing events.
- Event visibility is `public` or `private_link`. Private-link values are high-entropy, are returned only at creation or explicit rotation, and are stored only as domain-separated hashes.
- Event lifecycle is `draft`, `published`, `cancelled`, `completed`, or `suspended`. Duplicating any accessible event creates a new draft without registrations, private-link material, moderation state, or publication timestamps.
- Event instants are stored in UTC while retaining the selected IANA time zone. Published events must start in the future and end after they start.
- MVP registration methods remain `free` and `cash_organizer_confirmed`. Event-country policy controls allowed methods and deadline bounds. No payment-provider behavior is added.
- Public discovery exposes city plus optional district/general meeting area. Exact address, coordinates, and directions are returned only to event managers and members with `confirmed` or unexpired `cash_pending` registrations unless a manager explicitly marks the venue public.
- Phase 3 implements the venue projection against the existing registration table so Phase 4 can activate the same policy without changing the event API.
- Upload input is limited to 10 MiB and JPEG, PNG, or WebP. Verified images are decoded, orientation-normalized, stripped of metadata, and re-encoded to canonical WebP before attachment.
- Animated images, multi-frame images, malformed files, format/MIME mismatches, decompression bombs, polyglots with invalid trailing structure, dimensions outside 1–12,000 pixels, and images above the configured pixel ceiling are rejected and quarantined or deleted.

## Architecture

Talaqi remains a stateless FastAPI modular monolith backed by PostgreSQL. Phase 3 adds the bounded `media` and `events` modules already reserved by the engineering contract. Each owns its routes, schemas, domain models, service, repository, policies, adapter protocols, and focused tests. Routers call only their module service. Cross-module decisions use public interfaces from identity, profiles, regions, clubs, audit, and media; no module imports another module's repository.

The existing baseline `media_assets`, `events`, and `event_invite_tokens` tables remain authoritative. Phase migrations add only constraints or indexes that the implemented behavior cannot safely express with the baseline. Existing migrations and bootstrap assets stay byte-identical.

External object storage remains behind `MediaStorage` and `MediaService` interfaces. The local filesystem adapter is available only in development and tests. The S3-compatible adapter uses SigV4 grants and works with the existing MinIO service without exposing storage credentials to clients. Staging and production fail closed unless the S3-compatible adapter and durable rate-limit provider are configured.

Image decoding and canonical re-encoding use pinned Pillow `12.3.0`. Upload bodies are raw object bytes rather than multipart form data, so `python-multipart` is not introduced. API processes bound downloads to one byte beyond the 10 MiB limit and perform image work outside the event loop.

## Module boundaries and task sequence

### Task 3.1: Media asset pipeline

The media module owns upload intent creation, owner-scoped storage keys, signed upload grants, completion, canonical image verification, quarantine/deletion, abandoned-upload expiry, and verified-asset lookup.

`MediaStorage` exposes bounded operations to create an upload grant, read at most a supplied number of bytes, replace an object with canonical bytes, delete an object, and check readiness. `LocalMediaStorage` writes only below a resolved configured root and uses an expiring HMAC capability for its development upload route. `S3MediaStorage` creates path-style SigV4 URLs for the configured endpoint/bucket and performs bounded authenticated object operations. Neither adapter accepts caller-selected storage keys.

`POST /api/v1/media/uploads` requires authentication, CSRF, eligibility, and `Idempotency-Key`. It accepts only the safe original filename, declared content type, and declared byte size. It creates a pending database record before returning a short-lived upload grant. The storage key is derived from the authenticated owner and server-generated UUIDv7 asset ID.

The development-only signed `PUT` target accepts a raw body only when its HMAC capability, asset, declared length, and expiry match. It does not use an authenticated session and never logs the capability. S3-compatible deployments upload directly to object storage using the returned grant.

`POST /api/v1/media/uploads/{asset_id}/complete` requires the same owner, authentication, CSRF, and an idempotency key. Completion reads a bounded object, verifies exact byte length and declared MIME/signature agreement, decodes one frame, enforces dimensions and pixel limits, applies EXIF orientation, strips EXIF/XMP/ICC/text metadata, and re-encodes deterministic canonical WebP. Only after the canonical object has been persisted does the transaction mark the asset `verified` with final content type, byte size, dimensions, SHA-256, and verification time.

Failures never produce an attachable asset. Validation failures mark the record `quarantined` with a stable bounded reason and ask the adapter to quarantine or delete the bytes. Missing or transient storage failures leave the record pending and return a retry-safe error. Cleanup claims old pending records in bounded batches, deletes their objects, and marks them `deleted`. Verified assets are never cleaned by the abandoned-upload job.

`MediaService.require_verified_owned(asset_id, owner_user_id)` is the public interface used by profiles, clubs, and events. It reveals no cross-user asset existence.

### Task 3.2: Event domain and publishing

The events module owns create, get-managed, update, cancel, complete, delete-draft, duplicate, lifecycle policy, manager projection, and event audit history. It consumes the existing `CreationEligibilityService`, `RegionPolicyService`, club access service, `MediaService`, and `AuditService`.

Create and duplicate are idempotent. Updates and lifecycle actions require the expected revision and return `stale_revision` on conflict. All organizer mutations are authenticated, CSRF-protected, object-authorized, and covered by owner/admin/member/cross-object negative tests.

Publishing requires a future valid schedule, retained IANA zone, country/city/category, valid regional registration method and deadlines, positive capacity when supplied, paired coordinates, exact-venue disclosure choice, and an optional canonical verified cover owned by an authorized manager. Drafts may be incomplete but may not store structurally invalid values.

Cancellation and completion are explicit transitions with immutable audit evidence. Suspended events cannot be mutated by organizers. Delete is allowed only for drafts and removes only the draft event plus its private-link material; attached media remains owner-controlled and is not implicitly deleted. Duplicate copies safe editable content into a fresh draft and resets status, revision, publication/cancellation/completion/suspension fields, private-link token, and registrations.

### Task 3.3: Private-link access and venue disclosure

Private-link creation and rotation generate at least 256 bits of cryptographically secure entropy. The raw value is returned once in a URL fragment or explicit copy field so it is not sent as an HTTP referrer. The API resolver accepts the token in an authorization header or request body, never in a query string or route path. PostgreSQL stores only a domain-separated HMAC-SHA256 hash and expiry/revocation state.

Resolver attempts use a dedicated client/token-prefix rate-limit namespace. Logs, exception text, analytics, metadata, cache keys, and audit payloads never contain the raw token. Rotation atomically revokes the previous token. Revocation immediately removes access.

One audience-aware projection determines venue disclosure for public discovery, private-link detail, organizer preview, and later registration responses. It returns exact venue fields only when the server proves manager access, a confirmed registration, an unexpired cash-pending registration, or the event's explicit public-venue flag. Anonymous and merely private-link-authorized viewers receive only coarse venue data.

### Task 3.4: Shared event form and organizer operations UI

The web application uses generated API-client types and one schema-driven form for create, edit, and duplicate. It renders only server-returned ownership choices, regional policies, lifecycle capabilities, and validation blockers. It does not infer club roles or organizer privileges.

The form includes ownership, localized regional hints, schedule and IANA zone, visibility, cover media, capacity, registration method, deadlines, coarse and exact venue, coordinate pairing, and a disclosure preview. Organizer list/detail views include canonical preview cards, lifecycle actions, conflict recovery, loading/empty/error states, and an explicit Phase 4 attendee placeholder.

All visible copy uses translation keys with parity for English, Turkish, French, and Arabic. The complete organizer journeys pass mobile/desktop, keyboard, focus, screen-reader semantics, reduced-motion, long-text, and Arabic RTL checks.

### Task 3.5: Complete public club/event details

Discovery and web public-detail projections add canonical media, organizer trust/ownership summary, localized schedule, coarse venue/map, availability language, regional rules/cancellation summary, authenticated save state, club events, and deterministic rule-based related events.

Draft, suspended, cancelled where ineligible, and private-link content never appears in public lists, public fetches, metadata, sitemaps, server caches, or service-worker caches. Exact private venues and user-specific saved state never enter public caching. Canonical and alternate-locale metadata resolve only public eligible content.

## Request and data flow

1. The client creates an authenticated, CSRF-protected, idempotent upload intent.
2. The media service creates a pending record with a server-owned key and returns a bounded signed grant.
3. The client sends raw bytes directly to the selected storage adapter.
4. The authenticated client completes the upload; the API downloads only the bounded pending object.
5. The verifier validates, decodes, strips metadata, re-encodes, hashes, and replaces the object before marking it verified.
6. An organizer creates or updates an event through the events service.
7. The events service authorizes the server-owned relationship and calls published interfaces for eligibility, region policy, club access, verified media, and audit.
8. Public and private resolvers build audience-specific projections; private venue and token data never enter public read models.
9. OpenAPI generation updates the checked-in contract and TypeScript client; contract drift fails CI.

## Security and privacy rules

- Storage keys use only server-generated identifiers and fixed path segments. Original filenames are display metadata only and never participate in filesystem or object keys.
- Resolve and validate local storage paths after joining; every path must remain below the configured media root.
- Signed grants are short-lived, method-bound, key-bound, size-bound, and content-type-bound. Storage credentials and signing secrets never leave the API.
- Completion never trusts declared MIME, filename extension, dimensions, hash, or client completion claims.
- Image decoding is bounded by bytes, dimensions, pixels, frames, and processing time. Untrusted metadata is not copied to canonical output.
- Asset lookup failures are indistinguishable across missing, foreign-owned, pending, quarantined, and deleted assets where object existence would leak.
- Every cookie-authenticated mutation requires CSRF. Retryable mutations require idempotency. Organizer mutations have explicit negative object-authorization tests.
- Raw private-link and local-upload capabilities are absent from logs, audit payloads, exceptions, referrers, analytics, metadata, and cache keys.
- Public caches and service workers store only explicitly public projections. They never store upload grants, private links, organizer data, exact private venues, sessions, profiles, or attendee data.
- Production and staging reject local filesystem storage and require HTTPS S3 endpoints unless an approved loopback-only test configuration is used.

## Error handling

All endpoints retain the stable Phase 0 error envelope. Media validation uses stable codes such as `invalid_media`, `media_too_large`, `media_type_mismatch`, `media_dimensions_invalid`, `media_not_ready`, and `media_unavailable` without echoing filenames, object keys, hashes, storage responses, or decoder exceptions. Foreign-owned media resolves as `not_found`.

Private-link failures are generic and do not distinguish malformed, absent, expired, revoked, or mismatched values. Storage and image-library exceptions are translated at the service boundary; cancellation continues to propagate.

## Migration and compatibility strategy

Existing migration `0001` and all merged migrations remain byte-identical. Task 3.1 first proves whether the baseline media table supports the complete lifecycle; any missing invariant is added through one forward migration based on `0007_moderation_priority`. Task 3.2 does the same for events and invite tokens. Every migration runs upgrade, downgrade, and re-upgrade against PostgreSQL 18 and leaves exactly one head.

Public APIs evolve additively under `/api/v1`. Existing discovery event endpoints keep their public behavior until Task 3.5 extends their response models. No private venue field is added to an existing public schema without an audience-safe projection.

## Test strategy

Every task follows red-green-refactor. Focused unit tests run without network access through in-memory or temporary-directory adapters. PostgreSQL repository and migration tests use only the protected loopback `_test` database.

Media tests cover owner-scoped keys, safe filenames, path traversal, oversize and truncated objects, MIME/signature mismatch, malformed and polyglot inputs, decompression bombs, excessive dimensions/pixels, animation, metadata stripping, deterministic canonical output, hash/dimensions, foreign-owner denial, CSRF, idempotency, adapter contracts, quarantine, transient retry, cleanup races, and deployed configuration failure.

Event tests cover invalid schedules and IANA zones, country/city/category/method/deadline policy, coordinate pairing, exact-venue rules, independent limits, club owner/admin/member authorization, foreign media, stale revisions, lifecycle transitions, duplicate-as-draft, suspended principals/content, immutable audit evidence, and migration round trips.

Private-access tests cover entropy, hash-only persistence, one-time disclosure, rotation, revocation, generic failure, brute-force throttling, log/referrer/analytics exclusion, and the complete anonymous/member/manager/confirmed/cash-pending/expired/public venue matrix.

Web tests cover schema-driven form behavior, API-returned capabilities, create/edit/duplicate, conflict recovery, lifecycle actions, upload states, private-link copy flow, metadata/privacy exclusions, four locales, Arabic RTL, mobile/desktop, keyboard, focus, screen-reader semantics, long text, reduced motion, and production build.

## Commit, review, and GitHub delivery

The five product tasks use the exact master-plan commit subjects:

1. `feat: add secure media pipeline`
2. `feat: add club and independent events`
3. `feat: protect private events and venue details`
4. `feat: add event organizer workspace`
5. `feat: complete public event and club experiences`

Each task is implemented sequentially in the isolated Phase 3 worktree. A specification/security review precedes code-quality review. Critical and important findings are fixed and re-reviewed. The controller reruns the applicable complete gates, creates one focused task commit, pushes it fast-forward to GitHub `main`, verifies the remote SHA, and only then begins the next task.

After Task 3.5, a fresh review evaluates the complete Phase 3 range and the controller runs the Phase 3 acceptance matrix. Phase 3 exits only when eligible club and independent organizers can publish safe events, private links remain secret and unindexed, exact venue disclosure passes the full audience matrix, public experiences work in four locales, and all applicable migration, API, client, security, accessibility, build, and browser gates pass.
