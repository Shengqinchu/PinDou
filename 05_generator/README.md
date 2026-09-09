# Native Studio generator

This module is mounted by `05_studio` at `/tools`. It uses the host Vue router,
Pinia instance, account session, language, content store and design variables.
There is no independent HTML entry, login form or iframe. The old public tool
URLs are redirected by the Studio router; APIs and saved pattern files keep
using the existing generator service.

`SOURCE_MANIFEST.json` records the verified production source snapshot used for
extraction (release `20260909152214-studio-v6`). The original `05_web` working
tree and its unrelated pending backend changes were not merged or deployed.

Boundaries:

- Main account and tools use the same customer identity. Private caches and
  drafts are cleared when that identity changes. No token is copied into a URL.
- Short-lived IndexedDB drafts store a File and settings, plus an existing job
  ID. They expire after one hour. Refresh resumes a known job; an unknown POST
  outcome asks the user to check saved works before explicitly submitting again.
- Studio loyalty points/time and generator AI credits/passes are separate.
- Theme changes affect interface CSS only. MARD data, editing calculations,
  painting, and export payloads retain the verified source behavior.
- Production dimensions are 20–200 per side, aspect ratio 0.5–2. The old UI's
  1-cell hint was inconsistent with the deployed service and is corrected here.
- UI text uses `05_studio/src/content/generator*.json`; published owner edits
  remain authoritative. Tutorial screenshots have separate Chinese/English files.
- Native dialogs provide focus trapping, Escape, background inertness and the
  host scroll lock. Editor keyboard shortcuts do not run inside account dialogs.

Build from `05_studio` with `npm run build`. Local QA uses
`06_studio/qa_generator.py`, bound only to loopback port 19678, with an isolated
database and synthetic generator APIs. Run `verify-generator-stage1.mjs`,
`verify-native-generator.mjs`, and `verify-generator-interactions.mjs` from
`05_studio/scripts`. Real payment, live AI billing and native phone OS sheets
are outside those simulations.

Tutorial capture uses `capture-generator-tutorial.mjs` with the offline Standard
pattern fixture under `artifacts/generator-integration`; it never consumes paid AI.
The initial text migration script is retained as provenance, not a recurring
build step. Change archived copy directly for future edits.
