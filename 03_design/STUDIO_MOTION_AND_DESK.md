# PinDou Studio interaction and host desk

2026-09-07. User requests stronger motion on both customer and administrator interfaces, using their Turnitin and GitHub design rules.

## Located sources

- Current local T-Check: `C:/Users/123/Desktop/Turnitin_generation/docs/FRONTEND_INTERACTION_AND_MOTION_STANDARD.md`, source checkout `067008cfbd869cd548c78532ad269837cb01f97e`. The implementation source is `admin-dashboard/css/index.css` and `generate.html`. Read only; no T-Check edits. The named document is not present on that GitHub repository's default branch at the time of lookup, so local current guidance is the verified source.
- Owner's private [SaaS Playbook](https://github.com/Shengqinchu/saas-playbook): [frontend](https://github.com/Shengqinchu/saas-playbook/blob/master/spec/01-frontend.md) and [admin dashboard](https://github.com/Shengqinchu/saas-playbook/blob/master/spec/03-admin-dashboard.md), read via authenticated GitHub CLI. Verified default branch `master`, commit `746306d5f74aea2d9bb9b566fb2a064cc37b6ba5`. Connector returned no repository results; CLI access successfully found the repository.
- [Impeccable animate](https://github.com/pbakaus/impeccable/blob/main/skill/reference/animate.md) and [delight](https://github.com/pbakaus/impeccable/blob/main/skill/reference/delight.md): state continuity and feedback, with character tied to the product. Reference material, not a wholesale plugin install.
- [GSAP matchMedia](https://gsap.com/docs/v3/GSAP/gsap.matchMedia()/) and [Vue TransitionGroup](https://vuejs.org/guide/built-ins/transition-group.html): actual supported APIs, cleanup and reduced-motion behavior.

## What is changing

The previous implementation has a functioning protected manager and payment engine; its UI is still three long forms inside the public website. This pass creates a separate host workspace while preserving the existing server authority over payments, seating, prices and stock.

1. Shared interaction primitives: pressable buttons, animated selection indicator, switches, native modal drawers, visible success/error feedback and list continuity.
2. Customer site: a small bead assembly as the brand-specific focal motion; continuous selection, add-to-bag confirmation, animated basket changes and photo dialogs. Approved photography, English fonts and Chinese font families stay in place.
3. Host desk: its own navigation and compact layout, meaningful daily metrics from the entire database, searchable/filterable orders, detail drawer, weekly schedule and date exceptions, product editor, checkout settings, and paginated activity.
4. Validation: normal and reduced motion, interruption, keyboard focus/escape, touch, state preservation, failed saves, server authorization, truthful empty states, desktop and mobile layouts. Existing payment/booking contract tests remain required.

## Motion contract

- Controls inherit T-Check's 300ms ease-in-out, including nested icons, press and release. Stronger depth comes from layered shadows and a moving button surface, not a different timing on each element.
- Selection indicators travel between related choices. Drawers use a short side-entry and preserve focus. Save notifications appear only after successful server writes.
- The bead assembly runs once when the studio invitation is shown. Operational screens do not replay elaborate entrances on every tab switch.
- Prefer transform and opacity. No animation frame loop updates Vue state; no scroll hijacking; no simulated activity or invented sales graphs. No new animation dependency is necessary.
- Reduced motion removes spatial movement across both parent and child while keeping immediate, readable state changes. Touch does not depend on hover.

## Business boundaries

The merchant rate stays 1 CAD = 5 CNY. Real capacity, hours and tax treatment remain unconfigured until the owner sets them. Do not enable production purchasing for visual review. Test data stays in isolated local QA. Old generator routes and the existing dirty checkout remain untouched.
