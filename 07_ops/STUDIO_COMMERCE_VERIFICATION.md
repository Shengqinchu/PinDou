# Studio commerce verification — 2026-09-07

## Scope

Replaces public inquiry forms with a genuine mixed shopping bag, server-priced checkout, Hupijiao payment and automatically confirmed seats. Existing generator and its API/DB remain unchanged. Earlier studio requests remain queryable in the host desk.

## Runtime

- `06_studio/app.py` retains inquiry history and existing admin verification.
- `commerce.py` owns independent settings, catalog, orders, reservations, stock holds, events and checkout limits.
- `payments.py` uses authenticated outbound HTTPS and signed form callbacks; no production test gateway.
- Scoped merchant config: `/opt/pindou/studio/shared/.env`, mode 0600. Only existing PinDou merchant APP_ID, APP_SECRET, API_BASE_URL and studio public origin are copied. No original callback URL or other application secret is inherited.
- Unit loads that EnvironmentFile. The packer explicitly includes only app.py, commerce.py, payments.py and runtime dependencies. `qa_server.py`, tests and credentials are never packed.
- `qa_server.py` is exclusively a loopback local test server with a temporary database and test gateway. Its placeholder image explicitly says LOCAL QA ONLY. Never run this entrypoint on a public interface.

## Verified

- 37 backend contract tests pass: inquiry regression, atomic last-seat race, cart overbooking, day-pass intervals, quotes and exchange rate, inventory holds, payment/merchant/amount verification, independent provider verification, idempotent checkout, repeated callbacks, missing callback polling, gateway timeouts, hold expiry, late payment without overselling, order privacy, admin roles/versioning and fulfillment.
- Real origin merchant connectivity: create returned errcode 0; flat response hash verified; cashier and QR hosted by api.xunhupay.com. One explicit gateway-only RMB 0.01 diagnostic was created unpaid. Query returned WP, total_amount 0.01, payment_method four-wechat. No money was paid or refunded. The diagnostic is not a studio customer order and allocates no real seats.
- Browser test exercises mixed cart, quantities, persistence, checkout, local test cashier, verified local payment confirmation, admin schedule changes, and Chinese/English views at 360, 390, 768 and 1440 pixels. Evidence is in ignored `artifacts/studio-commerce/`.
- Local paid screenshots use the isolated test gateway, not real settlement evidence.
- The 19 browser states pass WCAG A/AA automated checks with no violations and no horizontal overflow after control transitions settle.
- Lost-response recovery test: gateway/order creation succeeds but the browser response is dropped; after page reload, resuming checkout retrieves the same order. Exactly one order was created. Mobile uses the cashier link without first displaying the QR. Goods-only confirmation correctly describes pickup, not a seat reservation.

## Deployed and verified

- Implementation commit: `10bedc3`.
- Release: `20260907215723-studio-v1`; archive SHA-256 `1ac443a9893e001c6b0aaab0c2aa583264638c8ccee3b6fe0bf425a3b7ec4862`.
- 53 packaged files verified. Nginx syntax check and studio health passed. Runtime version is `0.2.0`.
- Public browser checks: visit, shop, cart and manager at 390/1440 px, 8 pages total, no JavaScript errors or horizontal overflow. Separate home-page check covered Chinese/English, normal motion, mobile menu, admin sign-in and legacy `/upload` rendering.
- Live catalog: merchant configured, FX `5.0000`, capacity `0`, tax mode `unconfirmed`, online purchases disabled. Availability correctly returns `not_open`, no fictitious slots.
- Origin admin checks: anonymous 401, viewer 403, genuine existing admin token accepted for commerce and orders; private customer order requires its access key. Two exact synthetic legacy request rows were created, checked and removed; customer data was untouched.
- Original generator release stayed `/opt/pindou/releases/20260615074539-wallet-mode-labels`; old frontend index SHA-256 before/after `506f9bd2f9f0c37c52f08924f1504286816b93bff3198aea9f1790d0eceb36aa`. Both services remain active.
- Rollback/DB snapshot: `/opt/pindou/studio/backups/20260907215723-studio-v1/`, owner-only directory. Existing shared database was backed up with SQLite's online backup API before switching releases.

## Operational limits

Production remains closed to new purchases until the owner sets real opening hours/capacity and confirms tax treatment. Product previews have no invented price or stock. This is intentional business configuration, not a dummy payment button.

Do not claim a real successful debit or provider-origin paid callback has been tested: only actual unpaid gateway creation/query and isolated paid callback/fulfillment tests were performed. On the first real customer-approved payment, check confirmed seats, one paid event, exact frozen CNY amount and no duplicate inventory decrement.

## Repeatable checks

- `cd 06_studio; python -m pytest -q`
- Local browser run: `python qa_server.py`, Vite dev server, then `node scripts/verify-commerce.mjs` from `05_studio`. Stop both test processes after checks.
- Recovery checks: `node scripts/verify-commerce-recovery.mjs` against the same isolated local fixture. Read-only production: `node scripts/verify-commerce-live.mjs`.
- After UI copy changes: rebuild CJK subsets with `python scripts/build-cjk-fonts.py`, then `npm run build`.
- `python 07_ops/studio_pack.py`, verify archive allowlist/checksums, deploy using existing additive deployment script, verify new public routes and old generator assets.
