# ADR-010: Pegboard-Aligned Size Presets

Date: 2026-05-25

Status: Accepted

## Context

PinDou's previous size presets (`40x40`, `60x80`, `80x100`, `100x120`) were chosen as visual image-processing targets. User review with real pegboard workflows showed that this misses the physical making step: customers place beads onto plastic pegboards before ironing.

If the exported grid does not align with board dimensions, the customer has to manually decide how many boards to combine, where boundaries fall, and how much material is needed. This weakens the product's promise of "ready-to-make" patterns.

Research in `01_research/colormap/pegboard_sizes.md` shows a split:

- International 5mm square boards from Hama / Perler / Artkal commonly infer to 29 x 29 grids.
- The current China-first physical target from user feedback is a 26-grid domestic board sequence: 26 / 52 / 78 / 104.

## Decision

For Phase 2, PinDou uses domestic pegboard-aligned presets as the default:

- `26x26`: single board Q version
- `52x52`: double board
- `78x78`: triple board
- `104x104`: four board

The default generation preset becomes `26x26`.

The API field names remain unchanged (`size`, `size_preset`). Only enum values change.

### 2026-05-26 Amendment: Custom Sizes

User review after the v2 quality pass requested arbitrary board sizes in addition
to the four recommended presets. Phase 2 now allows custom integer `WIDTHxHEIGHT`
sizes with guardrails:

- minimum `20x20`
- maximum `200x200`
- aspect ratio between `0.5` and `2.0`
- non-26-aligned sizes are allowed, but the API returns a `metadata.warning`
  so the frontend can tell users that extra boards and edge trimming are needed

The recommended preset rail remains `26x26`, `52x52`, `78x78`, `104x104`.
Custom sizes are an advanced escape hatch, not the default product path.

## Consequences

1. Pattern dimensions now directly map to physical making tools for the current domestic target.
2. Preview and pattern exports can draw board boundaries at 26-cell intervals.
3. International pegboard support needs a future `board_profile` option, rather than overloading `brand`.
4. Old size values (`40x40`, `60x80`, `80x100`, `100x120`) are no longer product defaults and should be treated as legacy/internal only if needed.
5. Custom sizes may not align to physical boards; UI must surface the warning rather than silently implying ready-to-place boards.

## Follow-Up

1. Confirm the exact peg count of the user's MARD / Huangdoudou physical boards with photos or package labels.
2. Add `board_profile` to Phase 3 if PinDou exposes Perler / Hama / Artkal board-specific exports.
3. Add shopping-list coupling: `52x52` should recommend the relevant number of boards plus bead counts.
