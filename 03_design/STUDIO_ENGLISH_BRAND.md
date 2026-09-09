# English brand images — 2026-09-08

Owner request: replace the English logo with both supplied JPGs. Apply the plain mark to the English header and the contact version to the English footer. Chinese assets and unrequested copy remain unchanged.

| Asset | Original attachment | SHA-256 | Use |
|---|---|---|---|
| `english-mark-20260908.jpg` | `codex-clipboard-224d5cb2-6c0b-46c0-b100-e210a2c2cf35.jpg` | `f84d2e39880e6d45417c8eb97a101389adf98654660d9d04d6dcd0ee7aee191f` | English header, `brand-en` |
| `english-contact-20260908.jpg` | `codex-clipboard-ad9cd903-63c0-469b-a9b7-3234c54dafc9.jpg` | `fe1a4a6ee3e61bedb5a9465956233e5ff9d33807b1298cdf6eaa298aa13d747f` | English footer, `brand-en-contact` |

Both originals are 1280 × 1280, preserved byte for byte in `05_studio/public/studio-brand/`. `BrandMark.vue` uses a CSS viewport over y=455–960 for the plain mark and y=455–1250 for the contact mark. All black artwork stays inside the frame; no image generation, glyph substitution, tracing or lossy recompression.

`FooterBrand.vue` has separate non-overlapping home and WeChat hit regions. The WeChat region uses `CopyContact.vue`, at least 44px high, with keyboard focus, success toast and manual text fallback. It copies the ID actually written in the artwork. It is not nested inside a link. For a future uploaded replacement, the fixed contact hit region is removed because its text/location is unknown; the ordinary footer WeChat control remains available.

The content editor exposes the two English files separately. The shipped-default generator uses the new filenames, so later builds do not restore the previous mark. Only these two labels/metadata values are approved in the content ledger; no marketing copy was revised.

Verification and release evidence: `07_ops/STUDIO_ENGLISH_BRAND_VERIFICATION.md`.
