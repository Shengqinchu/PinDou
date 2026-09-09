# V5 wallet and website verification

Source and checklist: `02_product/STUDIO_VISION5_PROGRESS.md` (owner account PDF, v5 PDF, and 100-points clarification).

## Behavior delivered

- Verified shared email accounts gain a Studio time wallet and points ledger. Existing stable reservation owner IDs are backfilled without attributing anonymous bookings by contact details. Opening balances are entered by the host; example PDF balances are never seeded.
- Time is integer minutes, points are integers. Each completed attended website reservation awards100 points once; manual gifts permit88/188.100 points redeem CAD1, whole CAD only, within the eligible bill. Remaining points stay.
- Attendance minutes per guest and actual guest count are separate from booked minutes. The host separately records total wallet minutes used. Public guest notes and private host notes are isolated.
- Host entries use a SQLite write transaction, optimistic account version, UUID idempotency key, bounded amounts, and nonnegative balance constraints. An uncertain browser result retains the original request across refresh. Reversals append the opposite entry, retaining both originals and links.
- Booking deletion hides the record, with a deleted list and restore action. Confirmed reservations must first be cancelled. Recorded balances and ledgers do not disappear on deletion.
- Homepage cards read the latest3 full published diary posts, ordered by source date and publication time, and link to the actual articles. Address photo/text are brought closer. All7 process photos remain uncropped; the final3 are presented in a horizontal group.

## Local verification

- `python -m pytest 06_studio -q`: **118 passed**. The first full run had an intermittent pre-existing mocked journal-import failure; that exact case passed alone, then the complete118-test suite passed. No production diary data was involved.
- Wallet tests cover ownership/admin access, private-note exclusion, opening balances, gifts, top-ups, time debits, whole-CAD redemption with retained remainder, invalid amounts, insufficient funds, concurrent writes, duplicate retries, immutable entries/reversals, reward exactly once, future-visit rejection, booking ownership, deletion/restoration and ledger pagination.
- `verify-wallet-v5.mjs`: real local HTTP/UI flow in separate host/guest browser contexts:600-minute top-up,188-point gift,100-point redemption leaving88, commit with lost response followed by reload/retry, reversal, booked120 vs actual165 minutes,100-point attendance reward, deletion and restore. No browser JavaScript errors; English wallet renders.
- `verify-layout-v5.mjs`: **320,390,768,1024,1280,1440,1920,2560** widths, customer and host drawers, long forms and seven loaded photographs. Original photo ratios verified after lazy loading and fonts complete, with no horizontal page/panel overflow. Screenshots use reduced motion to capture settled layout, rather than an intermediate opening frame.
- Settled process rows are about1475px total on desktop (768px width:1467px); about2374–2379px on narrow portrait layouts. Text is allowed to reflow rather than clipped to an artificial screen height.
- Existing `verify-studio-regressions.mjs`: live editor input/preview acknowledgment, failed-save recovery, reconnect and publish, plus Windows native reduced motion with site full override, disabled Chromium native smooth scrolling, and WebKit.41/41/43 intermediate carousel frames observed; rapid changes, reversal, resize and preference persistence pass.
- `npm run build`: TypeScript and58 approved copy modules pass. All57 prior module hashes remain identical; only the newwallet module is added. The local Chinese body font subset was refreshed for the added interface words.
- Browser screenshots/data: `artifacts/studio-v5/`. Fixtures and tests are omitted from release packaging. Tests did not call a real SMS provider, payment gateway or WeChat authorization.

## Release

Pending final packaging and live verification. The publication will back up the current shared database and preserve owner overrides, current reservations, journal posts and business policy. Shared generator code is not included.

## Host workflow

1. Ask an old guest to sign in with email, then open **管理后台 → 顾客账户**. Locate their verified account and record the existing time using **老用户结余**.
2. Use **登记一笔** for a top-up, gift, time used, redemption or explicit correction. State the reason visible to the guest. Minutes used by several people are entered as the total across the group.
3. In **预约管理**, record actual minutes per guest, actual guests and the public note, then mark completed. This awards100 points once. Use **查看顾客账户** to record the corresponding wallet transaction when applicable.
4. To reverse a mistake, use **撤销这笔** and give a reason. If that reversal would make the balance negative, it is rejected for the host to reconcile rather than silently overdrawing.
5. Guests open **我的账号 → 我的账户／我的预约**. Opening the panel, returning to the visible tab or a15-second visible refresh reads the latest records; there is also an explicit refresh control.

## Limits

This release records verified offline balances; it does not collect online payments or enable the pending phone/WeChat providers. A completed legacy visit with no actual duration remains marked unrecorded until the host supplies it; deployment does not award historical points automatically. Tested mobile layouts are browser simulations, not a claim of physical iOS/WeChat device testing.
