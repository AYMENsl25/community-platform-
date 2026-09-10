# Talaqi UI/UX Upgrade Plan

Status: Sprint 0/1 implemented; launch follow-through planned
Baseline SHA: `4a36adebed19c2530427eaf917c70d40a9901efe`  
Baseline locale/data: English, deterministic local discovery fixtures  
Scope: Public discovery presentation only; no backend, route, permission, privacy, or business-logic changes

## 1. Current-state architecture

Talaqi is a pnpm monorepo. The public web application lives in `apps/web`, shared visual primitives in `packages/ui`, generated API contracts in `packages/api-client`, and localized copy in `packages/translations`. Next.js App Router server components own public data fetching and call `createServerPublicClient`; interactive behavior is isolated in client components such as locale selection, filters, save, and registration controls.

Public routes in scope are `/`, `/explore`, `/events/[id]`, and `/clubs/[slug]`. The existing filter contract uses `country`, `city`, `category`, `date_from`, `date_to`, `price`, `search`, and `cursor`. Sprint 1 will not create routes or query capabilities.

## 2. Current frontend stack

- Next.js 16.2.11 App Router, React 19, TypeScript 5.9.
- Node 24 and pnpm 10.34.5 workspace tooling.
- Tailwind CSS 4.3.3 is installed, but production presentation is primarily semantic global CSS and the small `@talaqi/ui` primitive package.
- Existing primitives: `ActionLink`, `Button`, `Card`, `Container`, `SkipLink`, `Stack`, and `VisuallyHidden`.
- No current shadcn, Radix, Base UI, Headless UI, React Aria, icon, or motion dependency.
- Vitest/Testing Library unit and integration tests; Playwright and axe browser coverage; lint, typecheck, build, formatting, OpenAPI, brand, security, privacy, RTL, and responsive gates.

Dependency decision: do not initialize shadcn or add a production dependency in Sprint 0/1. Apply its accessible composition principles to the existing system. A third-party dialog primitive requires a separate evidence-backed decision only if the custom sheet cannot pass its behavior tests.

## 3. Current UX problems

- The homepage promise is warm but abstract, while language and region controls compete with the primary discovery action.
- Real content begins too late and the page reads as a long document rather than a discovery feed.
- Desktop event cards place four text-heavy columns side by side; mobile cards become very tall metadata dumps.
- Event and community identity is not visually distinct enough, especially with repeated fixture imagery.
- Featured rationale repeats in every event card instead of being explained once at section level.
- The mobile header drops the brand and compresses desktop links into a row.
- `#community` and `#about` navigation targets are misleading outside the homepage.
- `/explore` shows both “Open filters” and the full form. The advanced dialog lacks a visible title, backdrop, inert background, and body scroll lock.
- Date fields have indistinguishable labels and active filters have no count or clear action.
- Missing or delayed imagery looks like an ambiguous blank block.
- The initial event-detail screenshot captured only `Loading`; it is retained as evidence of the baseline capture limitation and must be recaptured before detail redesign work.

Baseline screenshots are stored in `docs/ui-redesign/baseline/` for desktop home, explore, event detail, club detail, plus mobile home and explore. Final comparisons must use deterministic fixtures, locale, viewport, font, and reduced-motion settings.

## 4. Council verdict

### Where the Council Agrees

Modernize through a controlled presentation refactor, not a rewrite. Keep server components, existing primitives, URL-backed GET filters, routes, localization, and protected behavior. Add no dependency. Focus Sprint 1 on a branded responsive header, compact hero, scannable event/community cards, supported quick filters, a real filter sheet, skeletons, and responsive accessibility. The art direction is “calm local belonging”: warm, human, credible, and restrained.

### Where the Council Clashes

- Use responsive grids/lists in Sprint 1, not mobile carousels; rails can be evaluated later.
- Improve the existing custom filter sheet first; isolate any future primitive-library decision.
- Clamp discovery descriptions to two lines while preserving full detail-page copy.
- Keep prominent title/detail links instead of whole-card links where Save or nested links exist.
- Use a compact branded header with a menu panel rather than bottom navigation because stable top-level routes are limited.

### Blind Spots the Council Caught

Content and taxonomy quality, image rights/privacy/fallback behavior, measurement, browser history and cursor reset, translation governance, token blast radius, real Suspense/loading behavior, and deterministic screenshot data all need explicit safeguards. Visual polish must not conceal fixture-quality copy or invent popularity, distance, social proof, or personalization.

### The Recommendation

Use the existing architecture in reversible vertical slices. Establish compatible tokens and content contracts first. Then change only the public shell, homepage composition, discovery cards, URL-driven quick filters, custom filter sheet, and connected loading/responsive presentation. Run focused tests after each slice and full release gates at completion.

### The One Thing to Do First

Freeze the public discovery contract: exact routes, supported fields and filters, privacy-safe data, baseline conditions, and dirty files. Then make the compact event-card hierarchy conform to that contract.

## 5. Design principles

1. **Clarity:** explain local events and communities within five seconds.
2. **Discovery first:** show useful real content before asking for configuration.
3. **Trust:** emphasize truthful date, public place, organizer, price, and availability; never fabricate signals.
4. **Human connection:** use warm imagery and language without social-feed noise.
5. **Progressive disclosure:** quick URL filters first, advanced fields in a sheet.
6. **Mobile first:** recognizable brand, 44px targets, compact density, and no horizontal overflow.
7. **Inclusive by construction:** semantic HTML, visible focus, RTL, translated names, reduced motion, and WCAG 2.2 AA practices.
8. **Performance by default:** server rendering, narrow client islands, stable media geometry, and no animation library.

## 6. Design-system strategy

Extend `@talaqi/ui` without breaking existing consumers. Preserve current token values and add backward-compatible semantic aliases for canvas, surface, elevated surface, muted surface, primary, accent, text, muted text, border, success, warning, destructive, focus, type roles, spacing, radii, two elevations, and motion durations.

Shared tokens affect protected workspaces, so public visual changes should be scoped under `.tq-public-shell` where values would alter density or appearance. Brand-agnostic primitives may live in `packages/ui`; domain-specific discovery components remain in `apps/web`.

## 7. Component strategy

- `PublicShell`: public-only responsive header and route-safe navigation; never alter `WorkspaceShell` behavior.
- `EventCard`: image/fallback, category/price, title link, schedule, public meeting area, organizer, and secondary availability. Description is clamped; featured rationale remains section-level.
- `ClubCard`: explicit community identity, name, category, compact purpose, and location. Only show real counts supplied by the contract.
- `QuickFilters`: server-rendered GET links for supported categories and price; preserve unrelated parameters and reset cursor.
- `FilterDrawer`: one closed-by-default client island using the native GET form and the same query keys.
- `DiscoverySkeleton`: geometry-matched, assistive-technology-hidden visual placeholder connected to actual route loading.

Avoid boolean-heavy mega-components. Use a small explicit variant only where markup materially differs. Keep nested actions semantically independent.

## 8. Responsive strategy

- 375/430px: branded compact header and menu; single-column discovery; horizontally scrollable chips only; full-height/bottom-aligned filter sheet; 44px targets.
- 768px: two-column card grid when content supports it.
- 1024px: two or three readable columns.
- 1440px: capped content width, three or four event columns only when metadata remains readable, and deliberate whitespace.
- Use logical CSS properties for RTL. Test 200% zoom, long English/Turkish/French copy, Arabic RTL, missing media, and no horizontal document overflow.

## 9. Accessibility strategy

- Preserve skip link, landmarks, one meaningful H1, and ordered section headings.
- Menu and sheet controls expose names and expanded state.
- Filter sheet has a visible title, programmatic description, focus containment, Escape/backdrop close, focus restoration, background inertness, body scroll lock, and overscroll containment.
- Use distinct “From” and “To” labels, programmatic labels for all controls, and selected-state semantics beyond color.
- Skeleton rows are `aria-hidden`; one concise status announces loading where appropriate.
- Maintain visible `:focus-visible`, AA contrast, 44px targets, useful image alt behavior, and no hover-only information.

## 10. Animation strategy

Use CSS only. Limit motion to 140–220ms opacity, transform, border, and shadow transitions for menu/sheet state, controls, and subtle card feedback. Never use `transition: all`. Disable nonessential movement under `prefers-reduced-motion`; no parallax, long entrance, bouncing, or blocking transitions.

## 11. Performance strategy

- Preserve server-component fetching and current parallel requests.
- Do not wrap the homepage or result lists in new client boundaries.
- Keep fixed media aspect ratios and explicit dimensions; lazy-load below-fold covers and prioritize only genuinely above-fold media.
- Add no new production dependency and avoid duplicate primitive systems.
- Loading states must correspond to real route/Suspense behavior and approximate final geometry.
- Compare build/bundle output and investigate material client-JS or layout-shift growth.

## 12. Testing strategy

Focused tests cover shell landmarks/navigation, long and missing card data, unique links, query preservation, cursor reset, active count, Clear/Apply, focus entry/containment/restoration, Escape, inert background, scroll lock, RTL, and reduced motion.

Browser QA covers 375, 430, 768, 1024, and 1440px; English and Arabic; keyboard-only use; 200% zoom; missing images; long copy; Back/Forward filter history; privacy-safe fields; no horizontal overflow; and axe serious/critical and contrast findings.

Before completion run actual repository format, lint, typecheck, web/UI tests, build, targeted Playwright, accessibility, localization/RTL, privacy, registration, authorization, and security gates. Do not weaken tests or update snapshots blindly. Record infrastructure timeouts separately from product assertions.

## 13. Sprint breakdown

### Sprint 0 — audit and foundations

1. Preserve baseline screenshots, data/locale/SHA, and known capture limitation.
2. Document architecture, supported filters, and protected boundaries in this plan.
3. Add backward-compatible semantic token aliases and scoped public foundations.
4. Define event/community card, media, interaction-state, and localization contracts.
5. Establish focused behavior and responsive tests before broad visual changes.

### Sprint 1 — primary implementation

1. Public header/navigation only; keep workspace shells untouched.
2. Compact hero and homepage hierarchy with real content sooner.
3. Scannable event and community cards with stable missing-media treatment.
4. Supported quick filters with URL preservation and cursor reset.
5. Closed-by-default accessible advanced filter sheet with active count and Clear/Apply.
6. Layout-matched loading skeletons for these public surfaces.
7. Responsive, keyboard, RTL, reduced-motion, and browser visual QA.

Each slice should be separately reviewable and reversible. Stage explicit paths and exclude pre-existing dirty/generated files.

## 14. Risks

- Shared token changes can unintentionally restyle organizer/admin/member workspaces.
- A custom sheet can fail focus, inertness, scroll locking, or mobile browser behavior.
- Attractive repeated demo imagery can create false credibility and hide missing-media defects.
- Compact cards can conceal essential data or break with long translated content.
- Quick filters can misrepresent unsupported nearby/popular/personalized capabilities.
- Whole-card interaction can conflict with Save and organizer/community links.
- Skeletons can add code without appearing at a real loading boundary.
- English-only copy or inconsistent “club/community” terminology can regress localization.
- UI changes can accidentally affect service-worker caching or private media if protected modules are touched.

Mitigation: narrow file scope, compatible aliases, typed existing responses, real query links/forms, focused tests, deterministic fixtures, explicit image fallback, staged browser review, and no protected-module edits.

## 15. Protected architecture boundaries

Do not modify:

- `apps/api`, database schemas, migrations, OpenAPI contracts, generated API types, or API method behavior.
- `/api/public`, `/api/organizer`, `/api/admin`, or media proxy allowlists, path validation, cookies, CSRF, cache headers, or header forwarding.
- Authentication, authorization, role permissions/navigation, logout, moderation, organizer/admin operations, or protected routes.
- Save-event mutation semantics, registration/cancellation/waitlist/cash-deadline behavior, member communications, or idempotency.
- Private venue disclosure. Public cards/details continue to use only approved district/public meeting-area fields; exact venue remains eligibility-dependent.
- PWA privacy-safe caching, canonical URLs, route paths, pagination, locale direction, or server fetching ownership.

Existing dirty files at baseline are `apps/web/next-env.d.ts`, `apps/web/src/components/discovery/canonical-cover.tsx`, `.local-web.log`, and `apps/web/public/demo/`. They must not be silently reverted or mixed into unrelated commits.

## 16. Acceptance criteria

- Purpose, primary Explore action, and the start of real discovery are clear in the first 1440px and 375px experience.
- Talaqi identity and a valid discovery route remain visible at every required width; no dead hash targets or horizontal overflow.
- Event cards emphasize title, date/time, public place, category/price, and organizer; community cards are visually distinct; optional/missing/long/RTL data does not break layout.
- No invented distance, popularity, attendance avatars, recommendations, routes, fields, or social proof.
- Quick filters and the advanced sheet use the existing query keys, preserve unrelated state, reset cursor, survive reload/Back/Forward, and Clear all returns to `/explore`.
- Sheet opens with an announced visible title, contains focus, closes via Escape/backdrop/close, restores trigger focus, prevents background focus and body scroll, and works in RTL.
- All interactive targets are at least 44px, focus is visible, reduced motion is honored, and audited pages have no new serious/critical axe or contrast violations.
- Skeletons match final geometry and are connected to actual loading behavior; missing media has a deliberate, privacy-safe fallback.
- No backend, route, API, auth, authorization, privacy, registration, database, or protected workspace behavior changes; no new production dependency; no material client-JS increase.
- Relevant existing and new unit, integration, build, Playwright, accessibility, privacy, localization, and responsive gates pass, with exact commands/results reported.
- Before/after screenshots exist for the required public surfaces and representative widths, with any baseline limitation stated honestly.

## 17. Launch follow-through plan

This addendum converts the persona-test feedback into small, independently
releasable slices. It intentionally expands beyond the original public-only
Sprint 0/1 boundary, so each slice has its own authorization, privacy, and
browser gate. It does not change the closed-beta product boundary: no online
payments, invented social proof, public attendee data, or public exact venues.

### Slice A — visitor conversion at the registration boundary

**Outcome:** an anonymous visitor understands that registration needs an
account and has a clear, safe path back to the same event after sign-in.

1. Audit the existing authentication entry-point and its supported return-path
   contract. If it has no safe return-path contract, add one that only accepts
   same-origin, allowlisted Talaqi paths; reject external URLs and preserve the
   selected locale.
2. Replace the registration error-only experience with an inline, translated
   sign-in call to action after a `401`; retain the non-JavaScript/server error
   fallback. Do not disclose registration eligibility or private venue data to
   an anonymous visitor.
3. Add four-locale component coverage and Playwright coverage for: visitor
   opens event, chooses registration, reaches sign-in, returns to that event,
   and sees no exact venue before a confirmed registration.

**Exit gate:** return navigation is allowlisted, keyboard reachable, announced
by assistive technology, and passes the public-venue privacy assertions.

### Slice B — trustworthy event-state feedback

**Outcome:** members can immediately tell whether saving, registering, or
cancelling succeeded without relying only on a changing button label.

1. Give the existing save control a localized success status in addition to
   its pressed state; keep errors distinct and preserve the current CSRF and
   same-origin request behavior.
2. Add a compact registration-state summary beside the event action. It must
   use server-authoritative state after refresh and cover confirmed,
   cash-pending, waitlisted, cancelled, and retry/error states.
3. Make the private-venue explanation explicit with a non-sensitive lock cue
   and translated copy such as “exact venue shared after confirmation.” The
   cue must never imply the address, coordinates, attendee identity, or
   capacity outcome.
4. Validate screen-reader announcements, focus behavior, 44px mobile targets,
   reduced motion, long translated copy, and Arabic RTL.

**Exit gate:** no mutation reports success until the server refresh confirms
it; exact venue remains absent before the approved eligibility state and
disappears after cancellation.

### Slice C — organizer lifecycle persona fixture and browser suite

**Outcome:** the launch suite proves a club owner can complete an end-to-end
organizer workflow against deterministic, authorized fixtures.

1. Extend `scripts/testing/discovery-fixture-server.mjs` only with the
allowlisted organizer responses needed by the existing organizer proxy routes:
managed clubs/events, event create/edit/publish lifecycle, attendees, and
one-way event updates. Keep fixture state isolated per test and do not connect
to a real account or production API.
2. Add a serial Playwright persona journey for a club owner: open organizer
workspace, create or edit a draft, preview venue disclosure, publish with the
required confirmation/audit reason, inspect attendees, and publish a targeted
update. Add a separate negative journey proving a member cannot perform each
owner action.
3. Cover the existing independent-organizer workflow separately; do not make
club ownership a proxy for independent authorization. Run desktop, 375px,
keyboard-only, English, and Arabic RTL variants across focused tests rather
than one oversized mutable scenario.

**Exit gate:** both positive and denial paths use the local fixture, every
organizer mutation carries existing CSRF/idempotency/revision protections, and
the test suite is serialized to avoid shared fixture state.

### Slice D — production-mode test reliability

**Outcome:** a clean Windows checkout can produce the production build that
Playwright's `next start` web server requires.

1. Reproduce the missing `.next/BUILD_ID` condition in a clean worktree and
record Node, pnpm, Next.js, command, elapsed time, and final process result.
2. Diagnose the build interruption before changing application code. Check
webpack-specific build behavior, antivirus/file-lock interference, available
disk space, and stale `.next` state; do not treat a development-server result
as production-build evidence.
3. Add a narrow CI or local preflight assertion that fails clearly when the
production build artifact is absent, then run the persona suite under the
production web-server configuration.

**Exit gate:** `next build --webpack` completes from a clean state and the
visitor, member, club-owner, independent-organizer, and denial suites pass in
production mode with one Chromium worker.

### Slice E — dependency and launch governance

**Outcome:** launch decisions are based on current security and operational
evidence, not the historical release-candidate record.

1. Triage the GitHub dependency alerts by reachable package, affected service,
fixed version, upgrade compatibility, and severity. Patch or formally accept
each finding with an owner and expiry; do not suppress alerts to make the
count disappear.
2. Rerun the repository's documented dependency/security checks and attach the
exact SHA and results to the release record.
3. Complete the existing human gates: staging deployment/readiness, backup and
restore rehearsal, legal approval, product-owner acceptance across all five
personas, support/MFA setup, and monitored closed-beta decision.

**Exit gate:** no unresolved high-severity reachable dependency finding and no
open external release gate remain before a launch tag or public claim.

### Delivery order and release decision

1. Slice D first, because it restores production-mode evidence for every
other slice.
2. Slice A and Slice B next; they are narrow member/visitor improvements and
can ship as separate commits once their privacy gates pass.
3. Slice C follows with fixture support and serial browser journeys; it is the
evidence needed to validate the already-implemented organizer workspace.
4. Slice E runs in parallel as a release-management track, but does not block
implementation commits. It does block launch approval.

The product remains a **release candidate**, not launch-ready, until every
slice exit gate and the existing external approvals are recorded against the
same immutable commit SHA.
