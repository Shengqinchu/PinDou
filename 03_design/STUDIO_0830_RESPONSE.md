# Response to 最新项目0830 — implementation awaiting independent re-review

Baseline: `edaa3f8`; review: `STUDIO_0830_REVIEW.md`. The review and its `artifacts/studio-0830-review` evidence are preserved. This document maps the changes to the findings; it does not equate automated checks with design acceptance.

| Finding | Change | Verification |
|---|---|---|
| F01 | Visit has a complete catalog/readiness/availability recovery entry. Failed catalog stays an error. Unknown amount is null, never a zero fallback; date/guests/duration refs survive retries. | Consecutive catalog failure, successful recovery and availability failure preserve choices and restore correct price. `functional.json`. |
| F02 | Removed obsolete `.product` rules and competing image-label anchors from foundation/layout/typography. Product card, badge, title and price belong to commerce.css. Titles are 18px desktop / 16px phone; badges use one top anchor. | Actual title size, natural badge height, long Chinese/English names, 320/390/768/1080/1440/2048, Chromium/WebKit/Firefox. `layout.json`. |
| F03 | Metrics send explicit intent. Orders API distinguishes visit, creation and payment date; received includes verified funds needing follow-up. Fulfillment can be filtered. Ordinary navigation retains filters. | Old unpaid/search filters → current-day received, new-order and awaiting-fulfillment intents. Backend test includes an older order paid today and an order created today paid earlier. `functional.json`, `test_desk.py`. |
| F04 | Operational headings and product names use the Sans SC UI stack. Host title uses loaded Sans SC; key labels and explanations increased in their owner rules. Shop/visit/cart now have direct titles. | Chromium rendered-fonts reports PinDou Sans SC for the desk title, with no SimSun. Responsive and long-name screenshots. |
| F05 | Visit is intro → actual readiness/choices → room details on phones. Closed state has copyable host contact and optional price preview, without empty selectors. Homepage description is shorter and its auxiliary bead note follows the phone photograph. | First plan is within the 390px initial viewport; closed-state next action is also visible. No fabricated opening hours, capacity or stock. `layout.json`. |
| F06 | Removed the welcome photograph, reduced the greeting, put recent orders beside today's visits, added a follow-up entry and collapsed completed setup. Unfinished setup remains visible/actionable. | Recent-orders heading is around y=411 at 1440×900, compared with about y=900 before. Empty/configured/unconfigured states inspected. |
| F07 | Restored 300ms ease-in-out for controls/selection, retaining parent-child synchronization. Removed the global minimum-press latch. | Valid short press stops descending after release; long press/release, keyboard Space, double click and touch-pan cancellation pass. `functional.json`, `inputs.json`, desk resilience results. |
| F08 | Parent and bead assembly use one visibility-triggered timeline; parent finishes appearing before the beads assemble. It begins only when the note enters the viewport. Reduced motion shows the complete mark. | Frames with bead assembly in progress all have a visible parent. `functional.json`. |
| F09 | Switch has a 44×44 receiving button around a 44×26 visual track. Header/desk language targets and compact actions have real minimum target sizes. Phone product-name fields are separate rows. | Tap outside the track but inside the button toggles it. Header targets at narrow sizes and name-field geometry are measured. `functional.json`, `layout.json`. |
| F10 | Home clipboard denial shows a message and selectable WeChat ID; shop errors have a real catalog reload. Visit contact has the same fallback. Cart notices suppress a self-link when already in the cart. | Rejected clipboard and failed→successful shop reload pass. `functional.json`. |
| F11 | Photo viewer preloads the latest target, cancels older transitions, keeps at most current/target layers, and uses one caption. Current image stays visible while the next is slow or fails; retry is available. | Five rapid next clicks, reversal, delayed image, image failure→retry, Escape and scroll restoration pass. `functional.json`, `inputs.json`. |
| F12 | Product primitives have one owner; button states are in interactions.css; dialog geometry is in overlays.css; switch/segment internals are scoped in their components; host type is in desk.css. Removed retired photo/label selectors and the duplicated mobile container padding. | Source-selector audit plus computed style/font/geometry checks. Existing generator and unrelated dirty work remain outside this change. |

New focused evidence lives in `artifacts/studio-0830-fixes`. Populated prices/orders and editable fields on loopback are QA, not real merchant/customer facts. Long catalog names in layout checks are HTTP response fixtures and are never saved.

Completed implementation checks:

- 44 backend tests pass, including date/fulfillment alignment with overview metrics.
- Vue type check and production build pass.
- Focused functional checks cover F01/F03/F04/F06/F07/F08/F09/F10/F11.
- 80 focused layout records pass, with the requested six sizes and additional WebKit/Firefox coverage.
- The wider 179-record responsive/motion run passes. Its output is copied to `artifacts/studio-0830-fixes/responsive/results.json`.
- 32 host-desk states and 16 commerce states pass; lost-response checkout resumes one order; failed-save draft/retry and modal/menu focus/scroll behavior are retained.
- Keyboard, touch cancellation, slow/failed photography and WebView lifecycle checks pass.

Real iOS Safari, iOS WeChat and Android WeChat device tests are still unperformed. Browser engines, UA, safe-area and virtual-keyboard simulations are explicitly labelled as simulations. No real payment/refund or merchant settings were changed for this review. The public site stays closed to purchases until the owner supplies business settings.

## Re-review and deployment

To be filled after the reviewer examines the new implementation and after any resulting corrections. Production is still on the baseline release while this review is pending.
