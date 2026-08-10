# Phase 5 localization, accessibility, and responsive QA

This gate covers the critical public discovery and authenticated member journeys in English, Turkish, French, and Arabic.

| Quality requirement | Automated evidence |
| --- | --- |
| Dictionary parity | Translation parity tests require identical, non-empty keys for all four locales. |
| Arabic RTL and locale metadata | Playwright asserts `lang`, `dir`, localized headings, and the member dashboard in Arabic. |
| Long French and Turkish copy | Both locales run the complete 320 px home, Explore, and member-dashboard journey without horizontal overflow. |
| Keyboard and focus | The localized skip link is reached by keyboard and transfers focus to the main landmark. |
| Screen-reader semantics | Playwright inspects Chromium's computed ARIA snapshot in every locale and verifies the localized primary heading and locale-selector name exposed to assistive technology. This automates semantic exposure; native screen-reader voice and verbosity remain a pre-release device check. |
| Contrast | Axe's `color-contrast` rule runs explicitly on the home route in every locale, in addition to the complete serious/critical scan on all critical routes. |
| Reduced motion | Every locale journey emulates reduced motion, confirms the media preference, and verifies the primary action's computed transition durations are reduced to at most 1 ms. |
| Responsive layout | All four journeys run at 320 x 720 and assert document width containment. |
| Visual regression | Approved English desktop home and Arabic mobile member-dashboard baselines are stored with platform-neutral names. A small pixel-ratio tolerance covers OS font rasterization while preserving layout and content regression detection. |

Run the gate with:

```powershell
corepack pnpm typecheck
corepack pnpm lint
corepack pnpm test
corepack pnpm build
corepack pnpm exec playwright test tests/e2e/phase5-quality.spec.ts
```
