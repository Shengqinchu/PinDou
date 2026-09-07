# Studio host desk and motion — 2026-09-07

## Source and scope

The owner requested their existing Turnitin / GitHub design rules be found and applied to both the customer site and a complete administrator interface. The sources and design contract are recorded in `03_design/STUDIO_MOTION_AND_DESK.md`.

Located the current local T-Check motion standard and the owner's private `Shengqinchu/saas-playbook`, default branch master, commit `746306d5f74aea2d9bb9b566fb2a064cc37b6ba5`. Read the frontend and administrator specs. No changes were made to T-Check or the GitHub reference repository.

## Implemented

- Independent studio desk and sign-in at the existing studio manager route; the marketing header/footer are removed on this route.
- Overview uses whole-database order/payment metrics and Toronto date boundaries. Seven-day schedule contains actual confirmed and active held reservations.
- Server-side order search, status/date/type filtering and pagination. A protected details endpoint supplies notes, payment identity and event history to a native modal side drawer.
- Product editor drawer retains drafts when closed and provides an explicit saved-version reload after a conflict. Weekly hours, date exceptions, capacity and checkout settings remain editable with version conflict protection.
- Settings and product audit events record before/after snapshots. Activity has pagination and expandable changes.
- Shared 300ms controls, moving segment/nav selection, switches, modal drawers, add-to-bag feedback, shopping-bag/list transitions, gallery transitions and a short bead assembly in the public hero. No new animation library.
- Admin JavaScript and CSS are route-loaded; the main customer entry does not load the desk bundle. All secret/config authority stays server-side.
- Mobile navigation uses inert hidden content, bounded keyboard focus and Escape/scroll restoration. Native dialogs handle background inertness and focus restoration. Reduced motion removes spatial transitions.

## Checks

- 43 backend tests passed. New tests cover whole-database rather than first-page totals, search/filter correctness, held/expired/paid calendar entries, before/after audit snapshots, protected details, Toronto's 25-hour DST day, and authentication on every new endpoint. Existing payment/seat/stock and legacy inquiry tests pass.
- `npm run build` passes Vue type-checking and Vite production compilation.
- `verify-desk-motion.mjs`: 32 captured states across 1440×1000, 1080×665, 2048×1017 and 390×844, Chinese/English and normal/reduced motion. Final pass: no JavaScript errors, horizontal overflow or WCAG A/AA automated violations. Covers order search, native drawer Escape, stateful tab navigation, retained product draft, saves and audit.
- `verify-commerce.mjs`: 16 customer checkout states, no automated accessibility violations. Mixed bag, quantities, persistence, test cashier and payment confirmation still work.
- `verify-commerce-recovery.mjs`: lost-response retry created one order, mobile cashier and goods-only confirmation pass.
- Gallery opened, advanced and closed correctly; dialog dimensions stayed stable across sampled transition frames; body scrolling was restored.
- Desktop controls explicitly checked for common 0.3s parent/icon transition durations. Press/release and failure/mobile focus details are recorded by `verify-desk-resilience.mjs`.

Browser automation used Microsoft Edge (Chromium). Viewport emulation is not a physical Safari or WeChat webview check; those remain unverified. Screenshots and paid fixtures are isolated local QA, not real production customers or receipts.

## Production boundaries

This release preserves the existing merchant setup, fixed 1 CAD = 5 CNY rate and current closed-to-purchases settings. It does not invent hours, capacity, tax treatment, inventory or sales. No real payment or refund was executed for this design pass. Old generator code, routes and production service remain outside the change.

Deployment remains additive through `studio_pack.py` / `studio_deploy.py`, with file checksums, SQLite backup and prior-release rollback. Packer includes only production app/commerce/payments modules, never the QA gateway or tests.
