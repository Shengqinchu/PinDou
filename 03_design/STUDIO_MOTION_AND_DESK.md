# PinDou Studio interaction and host desk

> 2026-09-08 VISION2 更新：当前以 02_product/STUDIO_VISION2_PROGRESS.md、03_design/STUDIO_DESIGN.md 和 02_product/copy/STUDIO_COPY_RULES.md 为准。中文无衬线/白底手绘品牌；每组4人、总量不限、每日10–22点，营业时间与容量均后台可编辑；展示价格但保持人工确认。下文旧字段/视觉/固定周三四限制仅作历史参考。

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

## Current component and motion contract

The independent `STUDIO_0830_REVIEW.md` documents why the prior 480ms adaptation was rejected. A longer total duration still produced a faster first 100ms, and the retained press continued after release. That is superseded by the current contract below.

- Controls and selection use T-Check's 300ms ease-in-out (`cubic-bezier(.42,0,.58,1)`). Parent, child, shadow, down and release share that curve. `motion.ts` drives the CSS/GSAP clock; native active state follows the actual finger/key lifetime without a delayed latch.
- Hover belongs only to devices with a fine pointer and hover capability. Remove conflicting old rules instead of adding touch overrides. Host navigation leaves content stationary with a subtle opacity change coordinated to the indicator; selecting the current mobile menu item also closes the menu and restores interaction.
- Narrative/photo/modal timing is separate. Existing native modal focus, Escape, scroll restoration and interrupted close/reopen remain. Photos preload the target, keep at most two image layers, retain one caption and cancel stale transitions on repeated input.
- A reversed photograph fades back from its current blend, without discarding a partly visible layer. A third target waits only for the current blend to settle and its latest image to load; previous requests are canceled, not queued for playback.
- The bead graphic's parent and children share one timeline. It starts when the footnote enters the viewport; the parent appears before assembly. The phone photograph precedes that auxiliary note. Reduced motion renders the complete graphic immediately.
- Component ownership: product article/image/title/price/badge in `styles/commerce.css`; shared button states in `styles/interactions.css`; dialog geometry/surfaces in `styles/overlays.css`; switch and segment details in their Vue components; workspace type/layout in `styles/desk.css`. `layout.css` owns the single container gutter model, including safe areas. Stale `.product` and conflicting image-label anchors have been removed.
- Chinese editorial text uses Serif SC selectively. Product titles, practical controls and the host desk use the explicit Sans SC UI stack, including a Chinese system sans fallback for catalog text outside the static subset. Verify actual rendered fonts as well as CSS values.
- Practical pages have direct titles. On phones, a visit starts with readiness and choices; photos/details follow. An unavailable catalog stays an error, and a closed studio offers an actual contact/price-preview path instead of empty selectors.
- The host overview prioritizes visits, recent orders and follow-up. Completed setup collapses; unfinished setup stays actionable. Metric navigation carries explicit creation/payment/visit dates and fulfillment meaning; ordinary navigation keeps drafts and filters.
- Meaningful checks include catalog recovery without false zero prices, indicator/list semantics, card geometry, rendered Chinese fonts, actual touch hit targets, visible assembly and interrupted image transitions. Passing build/overflow checks is not visual acceptance.

## Viewports and WeChat

- `viewport-fit=cover`, safe-area padding and `VisualViewport` height/offset keep the modal header, scroller and footer within the visible area. Fallbacks work when `visualViewport` or `dvh` is unavailable. Pinch zoom is never suppressed or counteracted by the viewport handler.
- Shared counted body fixation restores the original styles and scroll position on close/unmount, including overlapping menu/modal lifecycles.
- Mobile time fields use their own full-width row, minimum 16px text, and native controls. Search/filter fields are included. Narrow, tablet, breakpoint boundaries, short landscape and ultrawide are separate checks.
- Cashier presentation is fixed for the current order page: handheld devices, including iPad desktop UA, use the mobile URL; desktop uses the provider QR. Rotation does not first display a QR then switch to a cashier URL. Pageshow/visibility return refreshes the verified order status.
- Primary references: [WebKit safe-area guidance](https://webkit.org/blog/7929/designing-websites-for-iphone-x/), [WebKit visual viewport and iPad desktop identity](https://webkit.org/blog/9674/new-webkit-features-in-safari-13/), [Hupijiao API contract](https://www.xunhupay.com/doc/api/pay.html). The provider explicitly distinguishes desktop QR and mobile URL, including WeChat handling. We do not invent a merchant JS bridge.
- Browser-engine checks and WeChat UA/keyboard simulation are not physical iOS/Android WeChat device verification. Report that distinction.

## Business boundaries

The merchant rate stays 1 CAD = 5 CNY. Real capacity, hours and tax treatment remain unconfigured until the owner sets them. Do not enable production purchasing for visual review. Test data stays in isolated local QA. Old generator routes and the existing dirty checkout remain untouched.
