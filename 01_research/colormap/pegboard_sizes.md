# Pegboard Size Research

Date: 2026-05-25

## Why This Matters

Pattern dimensions are not only visual presets. A customer places beads on a physical pegboard, irons the work, and removes the finished piece. If PinDou outputs a grid that does not map cleanly to the user's board layout, the pattern becomes harder to follow and harder to price.

## Findings

| Brand / channel | Bead size | Public pegboard evidence | Inferred grid | Confidence | Source |
|---|---:|---|---:|---|---|
| Hama large square midi pegboard | 5mm class / Midi | Product pages list 841 pins; 841 = 29 x 29 | 29 x 29 | High | https://www.hamabeads.com/product/interlocking-large-square-midi-hama-beads-pegboard/ ; https://hama.dk/en/products/midi-pegboard-large-square |
| Perler large clear square pegboard | 5mm class | Official page lists each board as 5.7 in square, 4-square as 11.375 in x 11.375 in. 5.7 in = 144.78 mm, close to 29 x 5mm pitch | 29 x 29 inferred | Medium | https://perler.com/products/large-clear-square-pegboards-4-ct |
| Artkal BP01-K large square pegboard | 5mm class / Midi | Official/manufacturer pages list 14.5 x 14.5 cm for 5mm midi beads. 145 mm / 5mm = 29 | 29 x 29 inferred | Medium | https://es.artkalfusebeads.com/products/artkalbeads-5mm-big-clear-square-pegboard ; https://artkalbead.com/artkal-beads-pegboard-5mm-fuse-beads-apply-to-product/ |
| Artkal BCP01 mini square pegboard | 2.6mm / Mini | Official page lists 14.5 x 14.5 cm for mini beads; grid count is not listed on the product page | Unknown / do not mix with 5mm | Medium for physical size, low for grid | https://www.artkalfusebeads.com/products/artkal-clear-large-square-pegboard-for-mini-2-6mm-beads-bcp01 |
| MARD / Huangdoudou domestic board | 5mm class | No stable official public spec found in this pass. User's physical target and requested sequence is 26-grid based: 26, 52, 78, 104 | 26 x 26 for Phase 2 domestic default | User-supplied / needs confirmation | User physical-board feedback, 2026-05-25 |

## Phase 2 Decision

For the current China-first MVP, PinDou defaults to the user's domestic 26-grid pegboard sequence:

| Preset | Grid | Physical interpretation |
|---|---:|---|
| Single board Q | 26 x 26 | 1 domestic square board |
| Double board | 52 x 52 | 2 x 2 domestic board area, compact |
| Triple board | 78 x 78 | 3 x 3 domestic board area |
| Four board | 104 x 104 | 4 x 4 domestic board area |

This is intentionally not claiming that Perler/Hama/Artkal large square boards are 26 x 26. Public international evidence points to 29 x 29 for common large 5mm boards. Phase 2 should ship a domestic default, while Phase 3 should add a `board_profile` selector if PinDou exposes international pegboard brands.

## Product Rules

1. A size preset must map to an integer number of physical board grids.
2. Cross-brand size assumptions are not safe. `brand` and `bead_diameter_mm` are not enough; future schema should include `board_profile`.
3. Cross-diameter board mapping is forbidden: 2.6mm, 5mm, and 10mm boards are separate physical tools.
4. Pattern export should draw visible board boundaries every board width, not only 10x10 guide lines.
