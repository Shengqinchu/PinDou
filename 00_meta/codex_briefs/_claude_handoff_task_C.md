# Claude Handoff — Phase 0 Task C Current State

> Date: 2026-05-24  
> Branch: `phase0`  
> Purpose: hand off the latest Task C findings for Claude review. Do not merge to `main` yet.

## 1. Phase 0 Status

All seven Phase 0 Codex tasks have a completed status in their task briefs. Task C is completed from Codex's PoC-execution perspective, but ADR-005a still must not be marked "passed" until the user runs 5-person subjective voting on the quantized / bead-preview outputs.

Recent Task C commits:

- `9a5dbe2 docs(phase0-task-C): run p1 api samples`
- `c73e1e5 docs(phase0-task-C): complete P1 PoC, vote pending user`
- `95fdbc0 docs(phase0-task-C): add bead domain prompt notes`

## 2. API PoC Result

P1 `gpt-image-2` via the OpenAI-compatible relay is working.

Tracked PoC outputs:

- `01_research/tech/poc_results.csv`: 40 P1 result rows
- `01_research/tech/poc_samples/`: 120 PNGs, three states per sample
- `01_research/tech/subjective_vote_template.csv`: 200 scoring rows

Observed metrics:

- P1 success: 40/40 in the tracked synthetic benchmark batch
- Latency: average 39.63 s, P50 33.13 s, P95 59.83 s
- P2/P3 skipped for this phase and left as Phase 2 provider candidates

Important: these tracked samples used synthetic inputs. They proved the pipeline, not commercial quality.

## 3. Product Direction Change From User Review

The user correctly pointed out that the synthetic inputs were too weak for judging product quality. We tested real/user-like materials in a private ignored directory and found:

- The better path is **photo -> Q-version / cute illustration -> bead finished-product preview**.
- The current PoC should optimize for a **finished product preview**, not the final strict grid pattern.
- The strict pattern should be generated deterministically by code after the user accepts a preview.

Private ignored outputs, not committed:

- `01_research/tech/user_poc_private/graduation_couple_q_chibi/`
- `01_research/tech/user_poc_private/pet_batch_20260524/`

Best observed private pet output:

- `pet_batch_20260524/outputs/kitten_gray_reference_style/kitten_gray_reference_style_ai.png`
- `pet_batch_20260524/outputs/kitten_gray_reference_style/kitten_gray_reference_style_bead_preview_80.png`

Best observed private human/couple output:

- `graduation_couple_q_chibi/v2_bead_friendly_flat_ai.png`
- `graduation_couple_q_chibi/v2_bead_friendly_flat_subject_bead_preview_80.png`

These files are intentionally ignored because they include user-provided / real-person or copyright-sensitive materials.

## 4. Key Finding: Prompt Needs Composition Constraints

In a graduation couple test, the model produced visible legs/feet that were not in the source crop. This happened because generic "big head, small body" Q-version prompts imply a full-body chibi character.

New required prompt constraints are documented in `01_research/tech/prompts.md`:

- Preserve the original visible body range and pose.
- Do not invent missing body parts.
- If legs, feet, shoes, or lower body are not visible, do not generate them.
- Do not change subject count.
- Remove background clutter, cars, license plates, text, and watermarks.
- Use thick black outline, large color blocks, minimal shadows, plain background.
- Target 12-18 solid colors, maximum 24 colors.

## 5. Bead Domain Knowledge Added

New doc:

- `01_research/tech/perler_bead_domain_notes.md`

Important domain conclusions:

- Finished preview and strict pattern are different deliverables.
- AI should generate a clean bead-friendly subject, not a fake grid chart.
- The app should treat white/transparent background as **no bead**, not white beads.
- Phase 1 should preview multiple sizes, e.g. 60x80, 80x100, 100x120.
- MARD 5mm middle beads are the recommended Phase 1 default, but MARD colors still need physical / reliable seller table validation.

## 6. Current Engineering Gaps

The quick private scripts proved the concept but are not product-ready. Phase 1 should implement:

- An input staging folder for user materials.
- A subject crop / mask stage.
- A provider prompt runner for Q-version preview.
- Size presets: 60x80, 80x100, 100x120.
- Background-as-transparent / no-bead handling.
- Post-quantization cleanup: isolated pixel removal, black outline protection, majority filtering.
- Preview output: round-bead product image.
- Pattern output: grid, color count, MARD color codes, PDF / Excel later.

## 7. Why Some User Images Were Not Run

The user later pasted several dog/person images in chat. Codex could visually inspect them in the conversation, but only a subset was materialized as local temporary files that Python could read:

- graduation couple photo
- ChatGPT bear screenshot
- gray cartoon cat
- gray kitten photo
- branded food cat image

The later dog and person images did not appear in `$env:TEMP`, `Downloads`, or the workspace as readable image files. They therefore were not sent through the API. Next step: put source images under:

`01_research/tech/user_poc_private/incoming/`

This directory is locally ignored through `.git/info/exclude`; real-person inputs and private outputs should not be committed.

## 8. Suggested Claude Review Questions

1. Should Phase 1 formally split output into `FinishedPreview` and `PatternSheet`?
2. Should ADR-005a acceptance focus on Q-version previews instead of realistic portrait preservation?
3. Should `StylizationProvider` return both AI preview and deterministic pattern metadata?
4. Should MARD 5mm be the only Phase 1 bead system, with Hama/Perler/Artkal left for Phase 2?
5. Should private user material runs stay out of git entirely, with only summarized findings committed?

## 9. Recommended Next Step

Ask the user to place real test images in `01_research/tech/user_poc_private/incoming/`, then run a new private batch:

- pet photo -> cute bead preview
- pet meme / sticker style -> original non-branded bead preview
- single human portrait -> constrained Q-version preview
- couple / group photo -> constrained Q-version preview

Do not claim ADR-005a is passed until the user completes the 5-person subjective vote.
