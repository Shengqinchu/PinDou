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

## Verified so far

- 37 backend contract tests pass: inquiry regression, atomic last-seat race, cart overbooking, day-pass intervals, quotes and exchange rate, inventory holds, payment/merchant/amount verification, independent provider verification, idempotent checkout, repeated callbacks, missing callback polling, gateway timeouts, hold expiry, late payment without overselling, order privacy, admin roles/versioning and fulfillment.
- Real origin merchant connectivity: create returned errcode 0; flat response hash verified; cashier and QR hosted by api.xunhupay.com. One explicit gateway-only RMB 0.01 diagnostic was created unpaid. Query returned WP, total_amount 0.01, payment_method four-wechat. No money was paid or refunded. The diagnostic is not a studio customer order and allocates no real seats.
- Browser test exercises mixed cart, quantities, persistence, checkout, local test cashier, verified local payment confirmation, admin schedule changes, and Chinese/English views at 360, 390, 768 and 1440 pixels. Evidence is in ignored `artifacts/studio-commerce/`.
- Local paid screenshots use the isolated test gateway, not real settlement evidence.

## Operational limits

Production remains closed to new purchases until the owner sets real opening hours/capacity and confirms tax treatment. Product previews have no invented price or stock. This is intentional business configuration, not a dummy payment button.

Do not claim a real successful debit or provider-origin paid callback has been tested: only actual unpaid gateway creation/query and isolated paid callback/fulfillment tests were performed. On the first real customer-approved payment, check confirmed seats, one paid event, exact frozen CNY amount and no duplicate inventory decrement.

## Repeatable checks

- `cd 06_studio; python -m pytest -q`
- Local browser run: `python qa_server.py`, Vite dev server, then `node scripts/verify-commerce.mjs` from `05_studio`. Stop both test processes after checks.
- After UI copy changes: rebuild CJK subsets with `python scripts/build-cjk-fonts.py`, then `npm run build`.
- `python 07_ops/studio_pack.py`, verify archive allowlist/checksums, deploy using existing additive deployment script, verify new public routes and old generator assets.
