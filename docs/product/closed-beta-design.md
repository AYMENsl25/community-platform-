# Talaqi MVP Through Closed Beta — Approved Design

**Date:** 2026-07-11
**Status:** Approved for implementation planning
**Sources:** `product-feature-specification.md`, `TALAQI_TECHNICAL_PRODUCT_PLAN.md`, `Talaqi_MVP_Architecture.html`, and `LOGO.png`

## Product decision

Talaqi will launch as a mobile-first community and events PWA for Turkey and Algeria. The closed-beta MVP helps adults discover local clubs and events, create clubs or independent events, join communities, and register through free or organizer-confirmed cash flows.

Online payments are excluded from the MVP. The registration model and provider boundaries must allow payments to be added later without changing club, event, or capacity ownership rules.

## Approved scope

- Email/password accounts, verification, reset, rotating sessions, profiles, and regional preferences.
- English, Turkish, French, and Arabic with complete RTL support.
- Public discovery by country, city, category, date, price type, and search text.
- Club drafts, automatic publication, open or approval-required membership, and scoped owner/admin roles.
- Public and private-link club or independent events.
- Free and organizer-confirmed cash registration, capacity locking, cancellation, expiry, and FIFO waitlists.
- Announcements, event updates, in-app notifications, and essential transactional email.
- Moderation, suspension/restoration, regional settings, immutable audit records, and admin MFA.
- Responsive PWA installation, accessibility, observability, deployment gates, operational runbooks, and a two-city closed beta.

Deferred: online payments/refunds, social feeds, chat, comments/reactions, native apps, QR check-in, recurring instances, revenue analytics, and ML recommendations.

## Architecture

- One monorepo containing a Next.js App Router PWA, a FastAPI modular monolith, a PostgreSQL-backed worker, generated TypeScript API client, shared UI primitives, and translation dictionaries.
- PostgreSQL 18 is authoritative for transactions, capacity, idempotency, audit history, and the transactional outbox. Redis is not required for the first beta; add it only when distributed rate limits or queue throughput require it.
- Backend modules communicate through service interfaces. Routers never call another module's repository directly. External email, storage, and monitoring providers sit behind adapters.
- The browser may render server-returned capabilities, but every mutation is authenticated, CSRF-protected, and object-authorized by the API.
- Static/public data alone may be cached by the PWA. Sessions, profiles, invitation tokens, attendee data, and notifications must never enter service-worker caches.

## Locked product rules

- Any email-verified member with a completed basic profile and accepted organizer/community rules may create a club or independent event.
- A new account may own one club and three active independent events. Admin-configurable trust limits may increase these values; limit reductions do not delete existing content.
- A club stays private until required profile fields are complete, then publishes automatically. Reports and risk signals are reviewed after publication.
- Club membership is either `open` or `approval_required`. Only the owner may grant or remove club-admin roles. A sole owner cannot leave without transferring ownership or closing the club.
- Events are owned by a club or one independent owner and are `public` or `private_link`. Private-link tokens are stored hashed and excluded from logs.
- Event-country policy controls registration methods and deadlines. MVP methods are only `free` and `cash_organizer_confirmed`.
- One active registration is allowed per member/event. `confirmed` plus seat-holding `cash_pending` registrations never exceed capacity. Waitlists are deterministic FIFO.
- Every registration transition records actor, reason, previous/new state, and UTC timestamp. Registration, cancellation, promotion, and cash confirmation are idempotent.

## Closed-beta defaults

- Audience: adults aged 18 or older. Date of birth is not collected; users attest that they are 18+ during registration. Minor participation is deferred pending a dedicated safeguarding policy.
- First cities: Istanbul, Turkey and Algiers, Algeria. Country/city tables remain configurable so later cities require data changes, not code changes.
- Required profile data: display name, username, country, city, locale, IANA time zone, preferred currency, and notification choices. No government ID or verification documents are collected.
- Venue privacy: public discovery shows city and optional district/general meeting area. Exact address, coordinates, and directions are returned only to event managers and members with `confirmed` or unexpired `cash_pending` registrations. A manager may explicitly mark a venue public.
- Turkey cash expiry: 24-hour default, configurable from 2 to 72 hours. Algeria: 48-hour default, configurable from 2 to 168 hours.
- Cancellation cutoff: 24-hour default in both countries, configurable from 0 to 168 hours and never after event start.
- Data retention: expired verification/reset tokens 30 days, revoked sessions 90 days, notification delivery logs 180 days, audit and registration-transition records 7 years. Account deletion anonymizes user-facing identity after a 30-day recovery window while retaining legally/operationally required audit records.

## Security and quality gates

- Argon2id passwords; HttpOnly Secure SameSite cookies; refresh rotation; CSRF; strict CORS/hosts; CSP, HSTS, `nosniff`, clickjacking, referrer, and permissions policies.
- Signed and size-limited uploads with signature validation, re-encoding, metadata stripping, path safety, and post-upload verification.
- Object-level negative tests for every organizer/admin mutation and concurrency tests for last-seat, duplicate-registration, expiry, cancellation, and waitlist promotion paths.
- All visible copy uses translation keys. Critical journeys pass keyboard, screen-reader, contrast, reduced-motion, mobile, and Arabic RTL QA.
- Production fails closed for unsafe secrets, cookie/origin settings, unavailable migrations, or admin accounts without MFA.

## Success criteria

The MVP is done when all critical member, club owner/admin, independent organizer, and platform-admin journeys work in four locales; security and concurrency suites pass; the PWA is installable; staging migration/restore and worker-recovery rehearsals succeed; legal/operational materials are published; and the Istanbul/Algiers closed beta can be monitored and supported without direct database intervention.
