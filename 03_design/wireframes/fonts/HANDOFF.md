# 前端实现 → Gemini Handoff Notes

This skin was designed in **M PLUS Rounded 1c** (Google Fonts) for the visual mockup. **Do not import a web font in production** — WeChat 小程序 restricts external font loading and the file would fail to fetch.

## Font stack for production

```css
font-family: "PingFang SC", "Helvetica Neue", Arial, sans-serif;
```

PingFang SC ships natively on iOS/macOS and is available on most modern Android distributions via system fallback. For the rounded feel:

- **Headlines / CTAs:** `font-weight: 600` (PingFang SC Semibold)
- **Body / labels:** `font-weight: 500` (PingFang SC Medium) — this is the closest visual match to M PLUS Rounded 1c's default weight
- **Captions / metadata:** `font-weight: 400`

Avoid `font-weight: 700` for Chinese body copy — it reads harsher than the mockup. Latin numerals and English fragments can still go to 700 if needed.

## Tokens stay the same

Everything else in `colors_and_type.css` (colors, radii, shadows, spacing, motion) maps 1:1 to small-program WXSS. Just translate `:root { --pd-* }` into WXSS `page { --pd-*: ... }` or inline constants and you're done.
