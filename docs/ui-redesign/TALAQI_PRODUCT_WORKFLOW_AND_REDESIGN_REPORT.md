# Talaqi Product Workflow and Redesign Report

Date: 2026-09-10
Scope: Product workflow, current technology, current backend capabilities, and a frontend/UI structure redesign plan
Repository area: `C:\Users\slima\Downloads\TALAQI\worktrees\phase-6-operations`

## 1. Executive summary

Talaqi already has the hard product foundation for a closed-beta community platform: public discovery, clubs, event publishing, registrations, member and organizer workspaces, moderation, audit trails, transactional notifications, and operational controls. The current problem is not that the backend is missing the core product. The problem is that the public frontend does not yet feel like a modern, image-led, user-friendly event discovery product.

The redesign should preserve the existing backend contracts and change the public structure, visual hierarchy, and interaction model. The target is a product that feels closer to a polished community/event platform: real event imagery, clearer discovery, better filtering, stronger event detail pages, and a more useful organizer/member flow.

The correct next move is a frontend redesign phase, not a backend rewrite.

## 2. Product goal

Talaqi is a localized, mobile-first community platform for Istanbul and Algiers closed beta. It helps verified adults discover safe local events, join communities, register for activities, and manage community participation.

The product should serve 3 primary personas:

- Visitor: explores public events and communities before creating an account.
- Member: saves events, registers, views their upcoming plans, and joins clubs.
- Organizer or club owner: creates clubs and events, manages registrations, communicates updates, and handles attendee operations.

The brand direction should be warm, trustworthy, local, and active. It should not feel like a blank admin system or a static documentation site.

## 3. Current app workflow

### Visitor workflow

1. Visitor lands on the public homepage.
2. Visitor selects or confirms region and locale.
3. Visitor opens Explore.
4. Visitor filters events by city, country, category, date, price, search text, and cursor pagination.
5. Visitor opens an event detail page.
6. Visitor can see privacy-safe public event details: title, image if available, schedule, category, organizer, price state, general meeting area, and availability language.
7. Exact private venue details remain hidden until the backend confirms the correct audience state.
8. Visitor is guided to sign in or create an account to save or register.

### Member workflow

1. Member signs in with a verified account.
2. Member completes profile, region, locale, and eligibility requirements.
3. Member saves events.
4. Member registers for free or organizer-confirmed cash events.
5. Member sees registration state such as confirmed, cash pending, waitlisted, cancelled, or expired.
6. Member accesses their dashboard for upcoming events, saved events, joined clubs, and notifications.
7. Member can cancel registration where allowed by the event policy.

### Organizer workflow

1. Organizer creates or manages a club or independent event.
2. Organizer uploads verified media through the media workflow.
3. Organizer drafts event details: schedule, category, capacity, registration method, location, and venue privacy.
4. Organizer publishes the event when the backend validates required fields.
5. Organizer manages attendees, cash confirmation, waitlist behavior, exports, and announcements.
6. Organizer actions are authorized server-side and audited where sensitive.

### Admin and operations workflow

1. Admin accesses MFA-protected operational tools.
2. Admin reviews moderation reports and cases.
3. Admin can suspend, unpublish, restore, or restrict entities through audited actions.
4. Operations can inspect feature flags, regional policy changes, and outbox delivery state.
5. Release operations use health checks, telemetry, rollback, backup, and restore procedures.

## 4. Current technology stack

### Monorepo and tooling

- pnpm workspace monorepo.
- Node.js 24.
- pnpm 10.34.5.
- TypeScript 5.9.
- Prettier, ESLint, Ruff, Pyright, Vitest, Testing Library, Playwright, axe, and Lighthouse.
- Root scripts for format, lint, typecheck, test, build, OpenAPI drift checks, brand checks, and E2E.

### Frontend

- Next.js App Router.
- React.
- TypeScript.
- Tailwind CSS is installed, but much of the production styling is currently semantic CSS plus shared primitives.
- `apps/web` owns public routes, protected workspace routes, API proxy routes, PWA behavior, and browser tests.
- `packages/ui` owns shared accessible primitives and design tokens.
- `packages/translations` owns four locales: English, Turkish, French, and Arabic.
- `packages/api-client` owns the generated TypeScript API client.

### Backend

- Python 3.13.
- FastAPI.
- Pydantic v2.
- SQLAlchemy async.
- Alembic migrations.
- PostgreSQL 18 as the source of truth.
- uv for Python dependency management.
- Modular-monolith structure with bounded modules.

### Worker and infrastructure

- PostgreSQL-backed transactional outbox.
- Worker app for delivery and scheduled operations.
- Docker Compose for local infrastructure.
- S3-compatible media storage, with MinIO used locally.
- Email adapter infrastructure.
- OpenTelemetry, alert rules, and operational dashboards.

## 5. Current backend capabilities to preserve

The backend already supports the main launch-critical product boundaries. The redesign should consume these capabilities through the existing API contracts instead of changing them.

### Identity and profile

- Email/password authentication.
- Verification and session flows.
- Member profile and preferences.
- Eligibility and capability checks.
- Locale and regional settings.

### Discovery

- Public event and club discovery.
- Filtering by region, city, category, date, price, and search.
- Cursor pagination.
- Public event and club detail responses.
- Search responses.
- Public/private response separation.

### Clubs

- Club drafts and publication.
- Membership policies.
- Join requests.
- Owner/admin/member roles.
- Member management.
- Organizer workspace support.

### Events

- Club-owned and independent events.
- Draft, published, cancelled, completed, and suspended lifecycle states.
- Capacity and registration policy.
- Verified media references.
- Private-link and venue-disclosure protections.
- Organizer event management.

### Registrations

- Free registration.
- Organizer-confirmed cash registration.
- Confirmed, cash pending, waitlisted, cancelled, and expired states.
- Capacity and waitlist handling.
- Attendee management and export support.

### Safety, moderation, and operations

- Immutable audit events.
- Moderation reports and cases.
- Admin actions with reasons and authorization.
- Feature flags and regional policy controls.
- Transactional outbox and retry operations.
- Security headers, rate-limit abstraction, CSRF protections, and proxy allowlisting.

## 6. Current design problem

The current public UI is structurally correct but emotionally weak. It does not yet communicate enough trust, local activity, or immediacy. The user should see real community energy in the first screen, but the current design feels too plain and too text-first.

Main issues:

- Not enough real imagery above the fold.
- Event cards do not feel rich enough to compete with modern event platforms.
- The homepage does not immediately show a strong event discovery experience.
- The visual system feels too flat and generic.
- Filters are functional but not inviting.
- The event detail page needs stronger visual hierarchy, better action placement, and clearer registration state.
- Club/community pages need stronger identity and belonging.
- The design does not yet make the app feel launch-ready to a normal user.

## 7. Redesign direction

The new frontend should become image-led and workflow-led.

### Public homepage

Replace the mostly explanatory layout with a live discovery-first screen:

- Large real-photo hero background or featured event image.
- Search and city/category controls in the first viewport.
- Featured events visible immediately below the hero.
- Category chips with icons.
- Clear path to Explore, Sign in, and Create community.
- No fake popularity or attendance claims unless returned by the backend.

### Explore page

Make Explore feel like the main product, not a filter form:

- Sticky search/filter bar.
- Large event cards with cover images.
- Category, date, location, price, and availability visible at scan speed.
- Mobile-first filter sheet.
- Map/list toggle can be added later only if backend location precision supports it safely.
- Empty states should suggest useful filter changes.

### Event card design

Each card should include:

- Stable image area with real cover media or a designed fallback.
- Date badge.
- Category and price chip.
- Strong title.
- Organizer/community name.
- Public meeting area only.
- Availability state.
- Save action for authenticated members.

The card must avoid showing exact private address, invented distance, fake attendee avatars, or fake ratings.

### Event detail page

The event detail page should become the conversion page:

- Large cover image at the top.
- Title, date, location, and organizer visible without scrolling.
- Persistent or prominent registration card.
- Clear registration state after user action.
- Privacy-safe venue explanation.
- Organizer/community panel.
- Related events below the main content.

### Club page

Club pages should communicate identity:

- Club cover and logo.
- Club purpose and category.
- Location and membership policy.
- Upcoming events.
- Join/request-to-join action.
- Community rules and trust signals returned by the backend.

### Member dashboard

Make it more task-oriented:

- Upcoming events first.
- Saved events second.
- Joined clubs third.
- Notifications and required actions in a compact side panel.
- Clear registration states.

### Organizer workspace

Keep it utilitarian and efficient:

- Dashboard summary: drafts, published events, cash pending, waitlist, recent announcements.
- Event creation as a guided form with progress.
- Media upload preview.
- Venue privacy preview.
- Attendee management table.
- Announcement composer.
- Clear destructive confirmations and audit reasons.

## 8. Recommended visual language

Use a more photographic, local, human visual language:

- Real event and venue photos where available.
- Designed fallback covers per category when no image exists.
- Warm neutral canvas, deep green brand, coral action color, and restrained blue/teal support color.
- Avoid a one-color theme.
- Use compact cards with 8px radius or less unless the existing design token requires otherwise.
- Use icons for actions and categories.
- Use strong focus states and high contrast.
- Do not use decorative gradient blobs or generic abstract backgrounds.

## 9. Frontend structure changes

The frontend can be restructured without backend changes by introducing a clearer public design layer.

Recommended structure:

```text
apps/web/src/components/public/
  public-home.tsx
  public-search-bar.tsx
  public-hero.tsx
  featured-event-grid.tsx
  category-strip.tsx

apps/web/src/components/discovery/
  event-card.tsx
  event-card-media.tsx
  event-detail-hero.tsx
  event-registration-card.tsx
  filter-sheet.tsx
  discovery-empty-state.tsx

apps/web/src/components/clubs/
  club-identity-hero.tsx
  club-event-list.tsx
  club-membership-card.tsx

apps/web/src/styles/
  public.css
  discovery.css
  event-detail.css
  club-detail.css
```

Keep shared primitives in `packages/ui` only when they are generic. Domain-specific components should stay in `apps/web`.

## 10. Image strategy

Images are the biggest missing design ingredient.

Recommended approach:

- Use organizer-uploaded verified media when available.
- Add deterministic local demo covers for development and screenshots.
- Add category fallback covers for events with no media.
- Give all images stable aspect ratios to avoid layout shift.
- Use meaningful alt text for event images and empty alt text only for decorative fallback artwork.
- Lazy-load below-fold images.
- Prioritize only the first above-fold hero/featured image.
- Do not use external hotlinked images in production UI.

Future backend enhancement, not required for the first redesign:

- Add image moderation metadata.
- Add multiple event images.
- Add image focal point/crop controls for organizers.

## 11. Accessibility and UX requirements

The redesign must keep or improve current accessibility:

- Use semantic buttons for actions and links for navigation.
- Every input needs a visible label or accessible name.
- Icon-only buttons need `aria-label`.
- Keep skip link and landmarks.
- Maintain one clear H1 per page.
- Keep visible `focus-visible` states.
- Keep filters URL-backed.
- Advanced filters should open in an accessible sheet with title, Escape close, focus restoration, scroll lock, and inert background.
- Use `Intl.DateTimeFormat` and `Intl.NumberFormat`.
- Honor reduced motion.
- Arabic must remain RTL-safe.
- Mobile controls should have at least 44px touch targets.

## 12. What should not change in this redesign

Do not change:

- FastAPI route behavior.
- Database schema.
- Alembic migrations.
- Authorization rules.
- Authentication, cookies, CSRF, or proxy security.
- Registration state machine.
- Private venue disclosure logic.
- Moderation, audit, or admin operations.
- PWA privacy rules.
- Generated API contracts unless a separately approved backend feature needs it.

This keeps the redesign focused and reduces launch risk.

## 13. Implementation plan

### Sprint 1: Visual foundation and public homepage

Deliverables:

- New public visual tokens scoped to public pages.
- Image-led homepage hero.
- Search-first homepage.
- Featured event section.
- Category strip.
- Mobile header improvements.

Verification:

- Unit tests for public home rendering.
- Playwright screenshots at 375px, 768px, 1440px.
- RTL screenshot for Arabic.
- Axe serious/critical check.

### Sprint 2: Explore redesign

Deliverables:

- Redesigned event cards with image support.
- Sticky search/filter bar.
- Mobile filter sheet.
- Better empty/loading/error states.
- URL-backed quick filters.

Verification:

- Filter URL tests.
- Back/Forward browser tests.
- Missing-image tests.
- Long-title and Arabic RTL tests.
- No horizontal overflow at 320px and 375px.

### Sprint 3: Event detail redesign

Deliverables:

- Large event media hero.
- Strong event summary area.
- Registration action card.
- Clear registration state feedback.
- Privacy-safe venue explanation.
- Related events.

Verification:

- Anonymous visitor journey.
- Member registration journey.
- Venue privacy assertions.
- Keyboard-only registration action.
- Save-event feedback tests.

### Sprint 4: Club/community redesign

Deliverables:

- Club identity hero.
- Upcoming event list.
- Membership action card.
- Community description and rules area.
- Clear organizer identity.

Verification:

- Visitor club detail journey.
- Member join/request journey.
- Long copy and RTL tests.

### Sprint 5: Member and organizer polish

Deliverables:

- Better member dashboard hierarchy.
- Organizer dashboard summary.
- Guided event creation layout.
- Attendee table polish.
- Announcement composer polish.

Verification:

- Member dashboard Playwright journey.
- Organizer create/edit/publish journey.
- Attendee management journey.
- Negative authorization checks remain covered.

## 14. Launch-readiness test plan

Before calling the redesigned frontend launch-ready, run:

```powershell
corepack pnpm --filter @talaqi/web typecheck
corepack pnpm --filter @talaqi/web lint
corepack pnpm --filter @talaqi/web test
corepack pnpm --filter @talaqi/translations test
corepack pnpm --filter @talaqi/web build --webpack
corepack pnpm e2e
corepack pnpm audit --audit-level high
```

Also run browser review manually with Playwright against:

- Desktop 1440px.
- Tablet 768px.
- Mobile 375px.
- Mobile narrow 320px.
- English.
- Arabic RTL.
- Missing images.
- Long event titles.
- Empty discovery results.
- Anonymous visitor.
- Signed-in member.
- Organizer.

## 15. Acceptance criteria

The redesign is ready when:

- The first screen immediately communicates that Talaqi is for discovering local events and communities.
- Real or intentional category imagery appears above the fold.
- Explore feels like a product feed, not a plain form.
- Event detail clearly drives registration without leaking private venue data.
- Member and organizer workflows remain intact.
- No backend security, authorization, privacy, or registration behavior changes.
- All relevant unit, typecheck, build, Playwright, accessibility, RTL, and responsive checks pass.
- Before/after screenshots are stored in the repo.
- The final branch and commit SHA are pushed to GitHub.

## 16. Practical recommendation

Start with Sprint 1 and Sprint 2 together as one bounded visual redesign branch. Those 2 sprints address the biggest issue: the app does not look image-led or easy to use. Event detail and dashboard polish should come after the discovery experience feels strong.

Recommended first implementation branch:

```text
phase-7/frontend-redesign
```

Recommended first commit sequence:

```text
docs: add Talaqi workflow and redesign report
feat: add public image-led design foundation
feat: redesign homepage discovery entry
feat: redesign explore cards and filters
test: add public redesign Playwright coverage
```

## 17. Key decision

The backend should stay as it is for this phase. The work should concentrate on frontend structure, image strategy, layout, copy, accessibility, and Playwright-verified user journeys.

