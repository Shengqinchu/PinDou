# Reference Samples

This folder stores public visual baselines used for Phase 2 quality tuning.

## Files

- `ai_target.png` — AI preview target. This represents the desired Q-version direction: flat solid color blocks, thick black outline, simplified facial features, and a cute sticker-like silhouette.
- `script_target.png` — Script / PatternSheet target. This represents the desired industrial bead pattern direction: visible grid, per-cell color code coverage, readable legend, and a layout that can guide real bead placement.

## How To Use

When tuning providers or exporters, generate a fresh sample from the same local private input image, then compare it against these baselines:

- AI path: compare silhouette simplicity, black outline clarity, color count, and absence of photo texture against `ai_target.png`.
- Script path: compare grid readability, per-cell code coverage, color legend clarity, and print-like structure against `script_target.png`.

Private user inputs stay under `01_research/tech/user_poc_private/` and must not be committed. These two target images are public reference samples and are allowed in git for quality review.
