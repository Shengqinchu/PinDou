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

## Motion contract — revised after code-level review

The owner rejected the first studio adaptation as fast and monotonous. T-Check itself still specifies 300ms ease-in-out. The studio's new durations below are an intentional response to that feedback, **not a claim that Turnitin uses them**.

- Actual source inspected: `index.html#help-card` (line 831) pairs lift with border and soft shadow. `generate.html` lines 99–147 defines the outer card, nested `.product`, soft `::before` surface, pressed scale, `.product-icon` lift and matched timing. The visual relationship matters more than copying a duration.
- `src/motion.ts` is the shared CSS/GSAP clock. Controls use 480ms `cubic-bezier(.22,.1,.22,1)`, including parent, inner number/icon, shadow, down and release. State indicators/list movement use 520ms; modal travel uses 680ms and exits use 480ms. GSAP CustomEase reads the same curve definition.
- Removed the prior hard button ledge, sweeping fill, diagonal icon wobble and uniform route opacity animation. Interactive plan/metric cards now carry their child labels/icons; informational cards remain still.
- Short taps retain the pressed visual for a minimum 180ms without delaying click, checkout, navigation or a save. Pointer cancellation, touch scrolling, blur and repeated input clear it; reduced motion does not add a retained transform.
- Native dialogs own focus and Escape. A full viewport shell has separate scrim and panel layers, animated by one interruptible timeline. Desktop details enter from the right; narrow portrait uses a bottom sheet. Close/reopen uses the current rendered frame, never a new from-state or a stale close callback.
- Photo switching crossfades in a stable stage. Images overlap; the footer and stage do not disappear while waiting for an out-in cycle. Previous/next respects direction. The public hero uses masked text lines and a slower photograph reveal; no per-character Chinese animation, no looping attention effects.
- Host navigation keeps mounted form state; the new view arrives in place. Slot refresh retains visible time cells (disabled while stale), with measured height continuity. Cart repricing keeps the prior summary shape explicitly marked as updating; only the fresh server quote enables payment.
- Prefer transform/opacity. Height animation is limited to the slot-result content whose size actually changes, with ResizeObserver cleanup and immediate reflow on viewport width changes. No Vue state writes per animation frame, no scroll hijacking, no invented activity.
- Reduced motion disables spatial transitions across both parent and child, including modal/hero GSAP. Coarse pointers do not rely on hover.

## Viewports and WeChat

- `viewport-fit=cover`, safe-area padding and `VisualViewport` height/offset keep the modal header, scroller and footer within the visible area. Fallbacks work when `visualViewport` or `dvh` is unavailable. Pinch zoom is never suppressed or counteracted by the viewport handler.
- Shared counted body fixation restores the original styles and scroll position on close/unmount, including overlapping menu/modal lifecycles.
- Mobile time fields use their own full-width row, minimum 16px text, and native controls. Search/filter fields are included. Narrow, tablet, breakpoint boundaries, short landscape and ultrawide are separate checks.
- Cashier presentation is fixed for the current order page: handheld devices, including iPad desktop UA, use the mobile URL; desktop uses the provider QR. Rotation does not first display a QR then switch to a cashier URL. Pageshow/visibility return refreshes the verified order status.
- Primary references: [WebKit safe-area guidance](https://webkit.org/blog/7929/designing-websites-for-iphone-x/), [WebKit visual viewport and iPad desktop identity](https://webkit.org/blog/9674/new-webkit-features-in-safari-13/), [Hupijiao API contract](https://www.xunhupay.com/doc/api/pay.html). The provider explicitly distinguishes desktop QR and mobile URL, including WeChat handling. We do not invent a merchant JS bridge.
- Browser-engine checks and WeChat UA/keyboard simulation are not physical iOS/Android WeChat device verification. Report that distinction.

## Business boundaries

The merchant rate stays 1 CAD = 5 CNY. Real capacity, hours and tax treatment remain unconfigured until the owner sets them. Do not enable production purchasing for visual review. Test data stays in isolated local QA. Old generator routes and the existing dirty checkout remain untouched.
