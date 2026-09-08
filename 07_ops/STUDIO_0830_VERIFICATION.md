# Studio 0830 review follow-up — 2026-09-07

The owner requested an independent review by the existing Turnitin task **最新项目0830**, followed by corrections in PinDou. The original review and evidence remain frozen. Changes address concrete rendering, interaction and task-flow problems; automated checks are not a claim that the owner has accepted the visual design.

## Review and implementation

- First review: `03_design/STUDIO_0830_REVIEW.md`, baseline `edaa3f8`.
- First correction commit: `e34120e42ed83cf374684efa1d1c4ab41b3e4412`.
- Finding-by-finding response: `03_design/STUDIO_0830_RESPONSE.md`.
- Second independent review: `03_design/STUDIO_0830_REREVIEW.md`; the reviewer confirms the main changes and specifies six remaining local P2 details.
- Final correction commit: `12a27b711daf280022ded60f49623a5e6b6239fa`. Removed old hover rules, coordinated stationary host navigation, preserved intermediate photo blends on reversal, closed same-item mobile menus, corrected Chinese line endings and localized network/accessibility text. The reviewer's independent closure evidence reports all six N1–N6 cases passing at this commit.
- Final independent report: `03_design/STUDIO_0830_CLOSURE.md`. The reviewer closed all six scoped issues, with no extra unresolved item, and explicitly ended the source freeze. Real-device and business boundaries remain as stated below.

Controls now follow the verified T-Check 300ms ease-in-out baseline, including parent/child synchronization and release. The artificial press latch was removed. Narrative and panel motion have separate timing. Bead assembly starts after its parent becomes visible. The photo viewer cancels stale changes, keeps at most two image layers and retains the current photo while the next loads or fails.

Product titles and badges have one CSS owner. Chinese operational headings render with the Sans SC UI stack; the host overview prioritizes visits and recent orders. Mobile visit readiness and selections precede photographs. The catalog retry restores the full catalog and availability flow without a false zero price. Metric links carry explicit creation/payment/visit date and fulfillment intent, while ordinary navigation retains filters and drafts.

## Local verification

All populated catalog, booking, customer and payment examples below belong to the isolated loopback QA server. No real charge, refund or merchant-setting mutation was used.

- Backend: 44 passing tests, including an older order paid today, an order created today paid on another day, and fulfillment/date alignment with overview metrics.
- Frontend: Vue type check, production build and rebuilt local CJK subsets pass.
- `verify-0830-fixes.mjs`: independent failure/recovery paths, metric navigation, actual rendered Chinese font, first-screen desk content, receiving targets, clipboard denial, native press return, visible bead assembly and interrupted photos.
- `verify-0830-inputs.mjs`: Space, double click, real CDP touch-pan cancellation, slow photography and failed photo retry.
- `verify-0830-layout.mjs`: 80 layout records; Chinese/English, long product names, 320/390/768/1080/1440/2048 widths with Chromium, plus representative WebKit and Firefox checks. Badges retain natural height; product titles resolve to 18px desktop / 16px phone.
- Existing responsive/motion suite: 179 records without reported runtime errors or failures, including breakpoint boundaries and narrow landscape.
- Host desk: 32 captured states; failed-save drafts/retry and menu/dialog focus/scroll restoration remain intact. Commerce: 16 states, lost-response recovery resumes one order.
- WebView lifecycle: 10 passing engine/UA/keyboard/safe-area simulations. List continuity: Chromium/WebKit outgoing geometry and rapid filtering pass.
- Final local follow-up: `verify-0830-polish.mjs` passes 19 focused records each in Chromium and WebKit. Touch release is checked after both copying outcomes. Photo reversals at about 25/50/75 percent keep their partly visible layer and fade it back before removal. Same-view navigation restores interaction/focus. Chinese line endings are measured at four widths.
- After the final corrections, the focused F01–F12 functional checks, keyboard/touch/slow-image/failed-image checks, checkout lost-response recovery and host draft resilience were repeated and pass. Network failure status 0 retains the existing uncertain-order replay behavior; duplicate orders remain zero in that QA scenario.

Focused raw evidence and screenshots: `artifacts/studio-0830-fixes`. Independent before/after reviewer evidence: `artifacts/studio-0830-review` and `artifacts/studio-0830-rereview`. These ignored artifacts stay outside the release archive.

## Live verification and release

Released after the six independent closure cases passed. This remains a studio development preview; it does not open sales or claim the owner's final visual acceptance.

- Release: `20260908010538-studio-v1`, replacing `20260907232410-studio-v1`.
- Archive SHA-256: `ec56c8ef1d83f521279530785cd99ff59978ffaa6fa0122418f42bd596e54814`; all 56 packaged files verified. Only studio static assets and the five intended service files were packaged.
- Backup and rollback location: `/opt/pindou/studio/backups/20260908010538-studio-v1/`, including the pre-release SQLite snapshot. Existing atomic-link deployment, health check and Nginx validation/reload passed.
- Public browser: `index-CzSQkSkP.js` and `index-DujWiNEA.css` loaded, with computed control clock `0.3s` and viewport-fit enabled. New Chinese copy, actual product title sizes and natural badge heights were confirmed at 390/1440; no reported runtime errors or page overflow.
- `verify-live.mjs`: desktop/mobile, Chinese/English home, mobile navigation, manager sign-in and legacy generator render correctly.
- `verify-commerce-live.mjs`: eight public visit/shop/cart/manage states pass. No checkout or customer submission was made.
- Read-only origin: commerce, orders, overview and activity return 401/403/200 for anonymous/viewer/admin respectively. Unknown public/private orders remain 404. The new received/payment-date query returns 200 (the old release returned 422 for its unsupported status). Health and both services are active.
- Evidence: `artifacts/studio-0830-polish/live-identity.json`, `origin-after.json` and live screenshots; public smoke records also remain in `artifacts/studio-qa` and `artifacts/studio-commerce/live`.

The original generator release remains `/opt/pindou/releases/20260615074539-wallet-mode-labels`; its before/after index SHA-256 is unchanged at `506f9bd2f9f0c37c52f08924f1504286816b93bff3198aea9f1790d0eceb36aa`. Production remains closed to purchases, capacity is 0, tax is unconfirmed, and FX remains 1 CAD = 5 CNY. No real merchant setting was changed.

Physical iOS Safari, iOS WeChat and Android WeChat checks have not been performed. Browser-engine/UA/keyboard simulations do not establish real-device compatibility. Real payment completion is outside this review's test evidence.
