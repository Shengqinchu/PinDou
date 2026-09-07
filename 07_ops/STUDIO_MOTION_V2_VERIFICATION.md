# Studio motion and WebView adaptation — 2026-09-07

## Source review and outcome

The owner rejected the first animation pass as too fast and uniform. Read the actual current Turnitin_generation `admin-dashboard/index.html#help-card`, `generate.html` card/product/icon/button selectors and `css/index.css`, alongside its motion contract. No Turnitin source or service was modified.

Turnitin's own baseline is 300ms ease-in-out. PinDou intentionally adapts the **relationships** with a slower studio cadence: 480ms controls, 520ms selection/state, 680ms modal entry, 480ms exit, and a roughly 1.1–1.5s editorial hero. CSS and GSAP read the same clocks and curves from `src/motion.ts`. Source mapping and primary references are in `03_design/STUDIO_MOTION_AND_DESK.md`.

- Replaced the hard button ledge and sweeping fill with soft elevation, inset press, and synchronised child movement. A short tap keeps its visual press briefly; the actual action is immediate.
- Separated modal scrim/panel, with native dialog focus and an interruptible GSAP timeline. Desktop details travel from the right; narrow portrait becomes a bottom sheet. Photos crossfade in a stable stage, without an empty out-in interval.
- Grid leaves snapshot all old cells before Vue changes layout; outgoing cards retain their dimensions and coordinates while remaining cards move. Height continuity is limited to actual slot/grid result changes, never an animation of the whole document.
- Slot refresh retains stale choices visibly disabled. Repricing preserves the previous summary shape, explicitly says it is updating, and keeps payment disabled until a fresh server quote exists.
- Host navigation is sticky and keeps mounted drafts and logical scroll position through the mobile menu's scroll lock.
- Viewport-fit, safe-area padding, visual viewport height/offset and a counted fixed-body scroll lock cover WebView keyboard/rotation cases. Native date/time, search, select and textarea controls retain at least 16px on touch/narrow displays. The focused drawer field is scrolled above its footer when the keyboard shrinks the viewport.
- Handheld cashiers include iPad desktop identity. A page does not switch between desktop QR and mobile URL after rotation. Returning via pageshow/visibility refreshes verified order state. This follows the [provider's desktop/mobile contract](https://www.xunhupay.com/doc/api/pay.html); no merchant JS bridge is fabricated.

## Validation

All commerce fixtures below use loopback `qa_server.py` and its fake gateway. No real charge, refund or merchant configuration change.

- `python -m pytest -q`: **43 passed**; existing payment, seat, stock, authentication and host API contracts.
- `npm run build`: Vue type check and production build pass. Chinese font subset rebuilt; all required characters already present, so font binaries and approved English/Chinese families are unchanged.
- `verify-responsive-motion.mjs`: **179 records, zero runtime errors, zero failures**. Chromium, WebKit and Firefox. Chromium sizes: 320×568, 360×640, 375×667, 390×844, 414×896, 600×800, 601×800, 767×900, 768×1024, 820×1180, 859×900, 860×900, 899×900, 900×900, 901×900, 1024×768, 1080×665, 1150×800, 1190×800, 1280×720, 1440×900, 1920×1080, 2048×1017, 2560×1440, 3440×1440, 844×390 and 1280×480. WebKit/Firefox repeat six representative narrow/tablet/desktop/landscape sizes. Home, visit, populated cart, schedule and drawers are covered; designated 390/1440 states have automated WCAG A/AA checks.
- Intentional mobile gallery scrolling is checked separately: the last tile can be brought fully into its scrollport. It is not hidden as a page overflow exception.
- First audit found real select/textarea cascade overrides and a keyboard-obscured focused field. Both were corrected before the passing repeat.
- Parent/child intermediate samples: at ~100ms, metric card y=-1.32416 and inner number y=-0.441387; at ~240ms, -2.59553/-0.865178; at ~520ms, -3/-1. The 3:1 displacement ratio stays constant. Both use 0.48s; short tap dispatch remains immediate. Photos retain stage geometry during overlapping crossfade and rapid close/reopen.
- `verify-webview-lifecycle.mjs`: **10 passing records** across Chromium/WebKit. Mobile draft/scroll return preserved 700px; interrupted drawer close/reopen retains draft; portrait→844×390 landscape keeps the body and dialog sized correctly; simulated 44px side/21px bottom safe areas protect input/footer. Android WeChat, iPad desktop identity and desktop WeChat presentation fixtures choose the correct cashier, retain it after rotation and refresh on return.
- `verify-list-continuity.mjs`: **2 passing engine records**. Outgoing product dimensions/coordinates stay fixed; rapid category changes clear temporary geometry correctly.
- `verify-desk-motion.mjs`: **32 captured states**, zero reported runtime errors, overflow or automated accessibility issues. Order filters/details, preserved drafts, settings saves, activity, Chinese/English, desktop/mobile and reduced motion.
- `verify-desk-resilience.mjs`: hidden mobile navigation inert, trapped focus, Escape/scroll restoration, failed save retains draft, successful retry, 0.48s parent/icon press/hover/release. Button measured idle y=0, hover=-2, press=+1 with scale .988, release=-2.
- `verify-commerce.mjs`: **16 states**, no automated accessibility violations. Mixed cart, quantity, persistence, local cashier and paid confirmation.
- `verify-commerce-recovery.mjs`: lost response/reload resumes one order, no duplicate, mobile cashier and goods-only receipt pass.

Screenshots and raw checks are ignored local artifacts under `artifacts/studio-motion-v2`, `artifacts/studio-desk` and `artifacts/studio-commerce`. The full-page capture of an open dialog includes the offscreen document below the visible viewport; header/footer visibility is independently checked by bounding boxes.

## Limits and production boundaries

WebKit on Windows is a browser-engine check, not an iPhone rendering guarantee. WeChat UA, visual keyboard and safe-area values are emulated; real iOS/Android WeChat client verification and real cashier completion have **not** been performed. Existing family/weight definitions are preserved; Windows WebKit font rasterisation is not used to redesign the approved typefaces. [Playwright documents the platform-dependent nature of WebKit testing](https://github.com/microsoft/playwright/blob/main/docs/src/browsers.md).

Production remains closed to purchases because capacity/hours/tax have not been supplied. Merchant configuration and 1 CAD = 5 CNY remain intact. This release changes only studio frontend/code/design guidance; old generator source, data and routing are preserved. Deploy via the existing manifest/hash, backup and atomic-link pipeline, with a post-release public check and old generator SHA-256 comparison.

## Deployment

- Implementation commit: `edaa3f8`.
- Release: `20260907232410-studio-v1`; 55 packaged files verified.
- Archive SHA-256: `f5d366a237caee9fd3d8bdadb8409d49fa03bd408655a5d8610feb8e66f59147`.
- Live entry verified in the browser: `index-DPHaiLyV.js`, stylesheet `index-Co6IqUbs.css`, computed control duration `0.48s`, viewport-fit meta present. Live photo panel/scrim, overlapping crossfade and scroll restoration pass.
- `verify-live.mjs`: Chinese/English home, normal animation, desktop/mobile menu, manager sign-in and legacy generator pass; no runtime errors.
- `verify-commerce-live.mjs`: 8 public visit/shop/cart/sign-in pages across desktop/mobile pass; no runtime errors or overflow.
- Nginx validation and service health passed; both pindou and pindou-studio remain active. Backend version remains 0.3.0 because its implementation was not changed.
- Origin checks were read-only. Commerce, orders, overview and activity returned 401 for anonymous, 403 for viewer and 200 for a short-lived existing-backend administrator token. Private unknown order stays 404. No synthetic production order/inquiry was written.
- Merchant configured, checkout closed, capacity 0, tax unconfirmed and FX `5.0000`, as before.
- Old generator release remains `/opt/pindou/releases/20260615074539-wallet-mode-labels`; index SHA-256 remains `506f9bd2f9f0c37c52f08924f1504286816b93bff3198aea9f1790d0eceb36aa`.
- Rollback files and pre-release SQLite snapshot: `/opt/pindou/studio/backups/20260907232410-studio-v1/`.
