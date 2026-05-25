# PinDou Mobile Adaptation Notes

Date: 2026-05-25

## Scope

This note defines how PinDou mini-program pages reserve space for the status bar, the WeChat capsule menu, and bottom safe areas across simulator and real devices.

## Three Layers

```mermaid
flowchart TD
  A["Physical screen"] --> B["Status bar: system time, signal, battery"]
  B --> C["WeChat capsule: menu / close button"]
  C --> D["PinDou custom title bar"]
  D --> E["Scrollable page content"]
  E --> F["Native tabbar + bottom safe area"]
```

Status bar: top OS chrome. Height differs by device, notch, Dynamic Island, and Android vendor skin.

WeChat capsule: the fixed right-side mini-program menu. Its top/height/width must be read at runtime with `uni.getMenuButtonBoundingClientRect()`.

Safe area: the bottom inset on iPhone X and later. On Android it is usually zero, but code must tolerate non-zero values.

## Device Rules

Use runtime data first:

- `uni.getSystemInfoSync()` for `statusBarHeight`, `screenWidth`, `screenHeight`, `pixelRatio`, and `safeArea`.
- `uni.getMenuButtonBoundingClientRect()` for capsule `top`, `height`, `width`, `right`, and `bottom`.
- Reserve right-side title/header space equal to capsule width plus right gap, so page titles do not sit under the native WeChat capsule.
- Use `safeArea.bottom` or `safeAreaInsets.bottom` for the bottom inset; also keep `env(safe-area-inset-bottom)` in CSS for iPhone X+ style runtimes.

## rpx / px Rule

Mini-program `rpx` is based on a 750-rpx design width. The practical conversion is:

`1rpx = screenWidth / 750 px`

Examples:

| Device | CSS width | 1rpx |
| --- | ---: | ---: |
| iPhone SE | 320px | 0.427px |
| iPhone 12/13 | 390px | 0.520px |
| iPhone 14 Pro Max | 430px | 0.573px |

PinDou currently uses `px` in the Vue/WXSS surface because the imported wireframes were px-based. For Phase 2, top chrome and safe areas are runtime px; future component spacing can move to rpx when the design system is normalized.

## Implementation Formula

In `App.vue`, initialize metrics at launch and store them in Pinia:

- `statusBarHeight = systemInfo.statusBarHeight || 20`
- `menuButton = getMenuButtonBoundingClientRect()` with a conservative fallback
- `topChromeHeight = max(statusBarHeight + menuButton.height + 8, menuButton.bottom + 8)`
- `capsuleReserveRight = max(screenWidth - menuButton.left + 12, 104)`
- `safeAreaBottom = screenHeight - safeArea.bottom`

In `MiniProgramLayout`, expose these values as CSS variables:

- `--pd-status-height`
- `--pd-menu-top`
- `--pd-menu-height`
- `--pd-top-chrome-height`
- `--pd-safe-bottom`
- `--pd-capsule-reserve`

The custom title row aligns to the real capsule's vertical position, while the title text reserves right-side width for the native capsule.

## Target Checks

| Device | Viewport | Expected behavior |
| --- | ---: | --- |
| iPhone SE | 320x568 | Header title remains readable; content scrolls; bottom footnote stays above safe area/tabbar. |
| iPhone 12/13 | 390x844 | Header aligns with capsule; upload title is not covered by the native menu. |
| iPhone 14 Pro Max | 430x932 | Dynamic Island/status bar does not overlap title; bottom safe area remains clear. |

## References

- uni-app CSS, safe area, and rpx: https://uniapp.dcloud.net.cn/tutorial/syntax-css.html
- uni-app system info API: https://uniapp.dcloud.net.cn/api/system/info.html
- uni-app menu button API: https://uniapp.dcloud.net.cn/api/ui/menuButton.html
- WeChat Mini Program `wx.getMenuButtonBoundingClientRect`: https://developers.weixin.qq.com/miniprogram/dev/api/ui/menu/wx.getMenuButtonBoundingClientRect.html

