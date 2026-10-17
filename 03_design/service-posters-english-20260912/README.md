# English service posters

Request: translate the three owner-supplied Chinese service posters into English, including replacing their logos with the existing owner-approved English logo.

Inputs: clipboard images ending `4916ea69-5a7e-4107-91d5-034cbfd3a0a2.jpg` (fusing), `40c60b42-d863-42d5-a319-ca45c5ec0013.jpg` (custom patterns), and `ff99a2d6-b48a-453f-a0f7-96e8b47de7ee.jpg` (assembly).

Logo: `05_studio/public/studio-brand/english-mark-20260908.jpg`, including Hamilton and PindouPuppy lettering, the hand-drawn dog, bone, stars and heart.

Method: built-in image_gen, one text-localization edit for each original poster. Preserve the owner's black-and-white hand-drawn style and illustrations. The prompts are saved alongside the outputs. Original images and the website are not overwritten by this artifact request.

## Deliverables

- [Bead fusing](bead-fusing-en.png) — [exact prompt](prompt-1.txt).
- [Custom patterns](custom-patterns-en.png) — [exact prompt](prompt-2.txt).
- [Bead assembly](bead-assembly-en.png) — [exact prompt](prompt-3.txt).
- [All three PNGs](english-service-posters.zip).

Each final generated image was visually reviewed for spelling, complete English copy, recognizable existing illustrations, the English Hamilton / PindouPuppy logo, unobstructed margins, and all numerical conditions. No Chinese lettering remains. Three built-in image_gen edits succeeded; no CLI/API fallback or separate image manipulation was used. Generated originals remain in the Codex output directory; these are unchanged copies saved in the workspace. Dimensions and hashes are recorded in `manifest.json`.

Translation notes: 85折 means 15% off; monetary amounts are CAD. Preserve 52 and 78 grid-size boundaries, 14 cm and 22 cm size descriptions, 50% deposits, three pattern revisions, three/five-day turnaround, 48-hour damage reporting, 50 CAD local-delivery and 100 CAD shipping thresholds. The source's grid-size range overlap at 52 is retained rather than silently changing its commercial terms.
