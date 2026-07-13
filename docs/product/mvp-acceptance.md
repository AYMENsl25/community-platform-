# Talaqi closed-beta MVP acceptance

## Locked product acceptance

- Audience is adults aged 18 or older, attested at registration; date of birth and identity documents are not collected.
- Launch cities are Istanbul, Turkey and Algiers, Algeria, with configurable country/city data.
- Supported locales are `en`, `tr`, `fr`, and `ar`; all copy uses translation keys and Arabic is RTL-safe.
- Email-verified members with complete profiles and accepted organizer/community rules may automatically create a club or independent event. New accounts may own one club and three active independent events; configurable trust limits may increase these values.
- Club drafts publish automatically when required fields are complete. Membership is `open` or `approval_required`; only owners change club-admin roles; sole owners must transfer ownership or close before leaving.
- Events are club-owned or independently owned, `public` or `private_link`, and use only free or organizer-confirmed cash registration.
- One active registration is allowed per member/event. Confirmed plus seat-holding cash-pending registrations never exceed capacity. Expiry/cancellation releases capacity and deterministic FIFO promotion is concurrency-safe and idempotent.
- Turkey cash expiry defaults to 24 hours (2–72 allowed); Algeria defaults to 48 hours (2–168 allowed). Cancellation defaults to 24 hours (0–168 allowed) and neither deadline passes event start.
- Public discovery exposes city and optional district/general area. Exact venue information is restricted as defined in [AGENTS.md](../../AGENTS.md).
- Expired verification/reset tokens are retained 30 days, revoked sessions 90 days, notification delivery logs 180 days, and audit/registration-transition records 7 years. Deletion has a 30-day recovery window then anonymizes user-facing identity while preserving required immutable records.

## Requirement-to-phase traceability

| Approved capability or boundary | Delivery phase |
| --- | --- |
| Repository contract, ADRs, deterministic toolchains, local services, PostgreSQL baseline/migrations, API/client contract, design shell, CI/security baseline | Phase 0 |
| Email/password identity, verification/reset/rotating sessions, profiles/preferences/eligibility, regions, Istanbul/Algiers configuration, four-locale RTL, public discovery/search, saved events, public web | Phase 1 |
| Club drafts and automatic publication, open/approval membership, owner/admin roles, ownership protection, immutable audit, moderation/admin foundation | Phase 2 |
| Secure media, club/independent events, public/private-link visibility, scheduling, venue privacy, organizer event workspace | Phase 3 |
| Free/cash registration, concurrency-safe capacity, cancellation, cash expiry, deterministic FIFO waitlists/promotion, attendee operations, PostgreSQL worker/outbox | Phase 4 |
| Announcements, event updates, in-app notifications, essential email, member/organizer dashboards, privacy-safe installable PWA, accessibility and four-locale completion | Phase 5 |
| Reports/moderation, regional operations, observability, security/privacy hardening, guarded deployment, backup/restore, retention/deletion, policies/support, Istanbul/Algiers release candidate | Phase 6 |
| Online payments and refunds | Deferred future boundary; no MVP implementation |
| Native iOS/Android apps | Deferred future boundary; reuse versioned API |
| Social feeds, chat/direct messages, comments, and reactions | Deferred future boundary |
| QR tickets and check-in | Deferred future boundary |
| Recurring event instances | Deferred future boundary |
| Organizer revenue analytics | Deferred future boundary |
| ML recommendations | Deferred future boundary; transparent rule-based ranking is allowed |

## Release acceptance

All role-critical journeys pass in four locales and Arabic RTL. Authorization-negative and concurrency suites pass, the PWA is accessible/installable/privacy-safe, no high or critical security findings remain, migrations and restore work, workers recover after restart, monitoring and runbooks are usable, legal/operational pages are published, and product-owner acceptance confirms the controlled two-city beta can operate without direct database intervention.
