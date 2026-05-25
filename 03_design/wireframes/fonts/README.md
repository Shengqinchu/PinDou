# Fonts

The brand calls for **PingFang SC Medium** (Chinese) and **Rounded M+** (Japanese/Latin) — both rounded sans-serifs.

## Substitution flag ⚠️

- **PingFang SC** is an Apple proprietary system font and is **not redistributable**. On-device it renders natively on iOS/macOS. For web/preview we fall back to the system stack: `"PingFang SC", "Hiragino Sans GB", "Microsoft YaHei"`.
- **Rounded M+** ships as TTFs from the M+ project but isn't on Google Fonts. We substitute **M PLUS Rounded 1c** (Google Fonts), which is the spiritual successor and visually almost identical — same authors, same rounded terminals.

If you have the real TTFs (PingFang SC, Rounded Mplus 1c), drop them into this folder and we'll wire them up with `@font-face` instead of the Google Fonts import.

Expected files (drop-in):
- `PingFangSC-Regular.ttf`
- `PingFangSC-Medium.ttf`
- `PingFangSC-Semibold.ttf`
- `rounded-mplus-1c-regular.ttf`
- `rounded-mplus-1c-medium.ttf`
- `rounded-mplus-1c-bold.ttf`
