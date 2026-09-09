# Native generator, wallet and timetable — 2026-09-09

Owner authorization: implement the audited integration plan with complete
Chinese/English UI; add attendance rewards of 166 points, a host booking
timetable, and wallet balances/history displayed in decimal hours.

## Release package

- Studio release: `20260909195017-studio-v7`.
- UI build: `2026-09-09T19:48:49.615Z`.
- Package SHA256: `38076f83e74b3b23cf105df7fd4b32ffd468c93f5e0a7eac57257b7ac80ddccc`.
- 351 verified files; incremental archive 2,680,469 bytes.
- Existing generator service remains `20260909152214-studio-v6`.
- Deployment status: live; Nginx validation/reload succeeded and both services are active.

## Behavior

- `/tools` is a native lazy-loaded Studio workspace with upload, loading,
  results, editing, works and tutorial routes. Header, account and language are
  shared with the main website. Old `/upload`, `/editor/:id`, `/result/:id`,
  `/works` and `/tutorial` links resolve through Studio compatibility routes.
- Interface styles use the Studio white/gray/blue palette and fonts. Editor
  height accounts for the host header; native dialogs trap focus, support Escape
  and lock background scrolling. Chinese/English tutorial images are current UI
  captures using an offline Standard-generation example.
- Known jobs resume after refresh. An unknown submission result is not
  automatically submitted again. Completion after leaving the waiting page
  does not steal navigation. Account changes clear private drafts and caches.
- Attendance reward is 166 for new qualifying records. Historical 100-point
  awards remain unchanged, with no duplicate awards or retroactive top-up.
  Redemption remains 100 points per CAD 1 in whole CAD amounts.
- Time balances and ledger entries display decimal hours (0, 0.5, 1.5, etc.).
  Storage and host entry retain integer minutes; no balance migration is needed.
- The host timetable aggregates all bookings in half-hour intervals and shows
  confirmed, pending and attended guests. Cancelled/deleted entries are excluded.
  Selecting a cell filters the reservation list. Latest host hours and blocks
  are read from the same service policy as the customer calendar.
- The deployed size contract is 20–200 per side with aspect ratio 0.5–2.
  The UI now validates it before submission. Unsupported HEIC and oversized
  files receive actionable messages; no automatic-compression promise remains.

## Verification

- Studio backend: **154 passed**, including new reward/history, aggregate beyond
  30-row pagination, date/time filtering, current policy, and OAuth return paths.
- Native workflow/layout: **58 checks passed**, including 50 page/language/width
  cases (five tool pages × two languages × 320/390/768/1440/2560).
- Interaction groups: **6 passed**: drop and file limits, exact custom-size request,
  DPR2 mobile pinch, PNG file-share payload/cancellation, short portrait/landscape,
  and bilingual quota dialog. Browser page errors: zero.
- Stage-one checks separately confirm a same-document header transition,
  preserved selected image across tutorial/back and language changes, and editing.
- MARD palette, palette manifest and pattern-editing calculations match their
  verified production source hashes. An offline 52×52 Standard example produced
  2,704 beads and 9 colours without a paid AI request.
- One journal-import test failed intermittently in the first broad run and
  passed in isolation; the subsequent full run passed all 154. No unrelated
  journal implementation was changed to mask it.

Test scripts are in `05_studio/scripts/verify-*generator*.mjs` and
`06_studio/test_timetable.py`. `06_studio/qa_generator.py` uses only a temporary
loopback database; it is excluded by the deployment packer. Detailed results
and screenshots are under `artifacts/generator-integration/`.

Live payments/paid AI and physical iOS/Android camera/share sheets are not
claimed as tested by the local simulations. Existing phone WeChat provider
limitations remain as documented in the authentication runbook.

## Data and rollback

Pre-release audit uses read-only SQLite fingerprints, exporting no customer
records. Wallet copy has no published/draft overrides, so the new 166-point
defaults take effect without overwriting an administrator edit. The deployment
backs up the Studio database, Nginx configuration and service unit before
switching. No generator DB or service upgrade is included.

Rollback: use the recorded previous Studio symlink and Nginx/unit backup under
`/opt/pindou/studio/backups/20260909195017-studio-v7`; keep the current shared
database and media so subsequent legitimate entries are not lost. The old
generator service/assets remain available at their unchanged release.

## Production acceptance

- Deployed Studio `20260909195017-studio-v7`, main bundle `index-DI0bQCGH.js`;
  all 351 deployed file hashes match the package manifest.
- Seven public native/legacy/account/manage paths return the new Studio entry
  with `Cache-Control: no-store`. Private API authority remains server-enforced.
- Pre/post release fingerprints match for all audited account, artwork,
  reservation, policy, journal, credit, membership, identity and wallet tables.
  Original generator release and HTML hash are unchanged. NTP remains synchronized.
- Codex in-app browser opened the native tool with the existing signed-in user,
  displayed the correct unlimited generator allowance, and opened the shared
  account drawer showing its existing WeChat binding and `0 小时` balance.
- Code commit: `4d5fa01`, pushed to `codex/studio-v1-20260907`.

- The live account tooltip confirms 166 points per attended booking and the unchanged 100 points = CAD 1 redemption rate.
