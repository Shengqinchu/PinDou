# Windows Chrome 菜单位移与动画偏好修正

## 当前默认规则：2026-09-09 店主再次明确要求

店主：“必须让大家第一次进来就有动画的呀”。本次线上复现：本机原生 Chromium 与当前应用浏览器均报告系统 `reduce`，无本地选择时解析为 `system/reduced`，标题悬停 transform 为 none；同一系统显式 full 时标题正常抬升。无痕没有普通窗口保存的 full，因而暴露了原默认规则。

新规则覆盖下文 09-08 的默认行为：没有本站选择（含存储不可用／无效）时默认完整动画；显式 full、reduced、system 均保存并跨标签同步。system 现在必须保存字面值，清除该键代表回到完整默认。系统媒体查询只在访客主动选择 system 时决定动画开关；不修改 OS 设置。后台标签、离屏与触摸滚动的正常节流／取消逻辑保留。

修改点仅限 motion-preference.ts；现有 CSS、标题、小狗、星星、按钮、弹层、预约与生成器仍读取统一解析结果。首个组件挂载前同步模式，旧显式减少动效选择不强制覆盖。当前验证与发布证据见 `07_ops/STUDIO_MOTION_DEFAULT_VERIFICATION.md`；下文是此前故障和当时策略的历史记录。

2026-09-08。店主反馈：右上菜单打开时整个页面抖动/错位；Windows Chrome 的 `https://pindoupuppy.com/studio/visit` 没有录屏中的连续动画。保持已批准文案不变。

## 可重复的原因

### 1. 滚动条消失后才测宽度

2105×1193 的 Windows Chromium，启用真实经典滚动条时：

| 状态 | viewport | clientWidth / body | 首页照片 x |
|---|---:|---:|---:|
| 打开菜单前 | 2105 | 2090 | 477 |
| 原实现打开菜单后 | 2105 | 2105 | 484.5 |
| 原实现关闭菜单后 | 2105 | 2090 | 477 |

`lockPageScroll()` 原先先设置 `body.position=fixed`，随后才读取 `documentElement.clientWidth`。正文脱离文档流后，15px 滚动条消失，读取到的是变宽后的尺寸，居中内容因此移动 7.5px。

修正为：锁定前保存内容宽度和滚动条占位；锁定过程中保持该宽度；窗口改变尺寸时保留相同占位；最后一个锁释放时恢复原内联样式与滚动位置。保留已有的计数与幂等释放机制。

此前默认无头浏览器隐藏滚动条，宽度始终为 2105，未复现真实窗口的变化。新的回归明确去掉 `--hide-scrollbars`，并断言滚动条占位必须大于 0，禁止在没有滚动条的环境中宣称通过这项检查。

### 2. 录屏环境覆盖了系统动画偏好

本机原生设置复测（`reducedMotion: null`）时，Windows Chromium 和 Firefox 报告 `prefers-reduced-motion: reduce`。旧 CSS 的 11 个降动效区块把过渡关闭，JS 又同步跳过了按钮反馈、价格展开及弹层动画。强制 `no-preference` 的录屏自然与这个环境不同。

[Playwright 的 reducedMotion 配置](https://playwright.dev/docs/api/class-browser#browser-new-context-option-reduced-motion)说明默认模拟 `no-preference`，`null` 才恢复系统行为。系统偏好对网页的含义见 [MDN prefers-reduced-motion](https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-reduced-motion)。本次确认的是同机原生策略复现；已有 Chrome 标签未启用远程调试，因此没有假称读取了该标签的运行状态。

## 网站独立选择与统一实现

`src/motion-preference.ts` 作为唯一入口，同时驱动 CSS、GSAP 和短按反馈。原分散的降动效 CSS 移至 `styles/reduced-motion.css`，统一以 `html[data-motion="reduced"]` 作为生效条件。禁止再单独给某一组件读取原生媒体查询，造成 CSS/JS 一部分开启、一部分关闭。

| 链接参数 | 本站行为 | 保存方式 |
|---|---|---|
| `?motion=full` | 本站完整动画 | 保存到本浏览器的 `puppy-studio-motion` |
| `?motion=reduced` | 本站减少动态效果 | 保存到本浏览器 |
| `?motion=system` | 跟随系统 | 移除本站覆盖值 |
| 无参数 | 使用本站保存的选择；没有选择则跟随系统 | 不改写偏好 |

这个选择不修改 Windows 或 Chrome 的全局设置，也不强制其他访客开启动画。打开完整模式链接一次后，普通 `/studio/visit`、刷新、页面切换均保留选择。跨标签更新会同步生效；系统模式仍随 OS 变化。存储不可用时，当前页面仍遵循显式 URL 选择。

`ui.ts` 继续提供原来的 `reducedMotion()` 调用接口。首页 GSAP context、价格 AutoHeight、modal、相册与 press 反馈读取同一个有效值。首个 Vue 组件挂载前设置模式，避免初始帧先使用另一套规则。

排查当前标签可读取 HTML 根节点的 `data-studio-build`、`data-system-motion`、`data-motion`、`data-motion-source`，分别表示实际加载版本、系统请求、最终模式和选择来源。这些只包含公开构建/显示状态，不包含账号或预约数据。

## 验证

- `verify-runtime-preferences.mjs`：真实经典滚动条、系统原生媒体偏好、完整/减少/系统模式、普通预约地址与刷新后的保存、跨标签同步、草稿保留。
- 菜单在页面顶部、滚动 700px 后、2105px 窗口缩至 1080px 后，打开/关闭的照片横向位移均为 0px；滚动位置恢复正确。
- 在系统明确要求 reduce 时，本站 full 模式的套餐卡片上浮 -4px，价格约 90ms 时仍在中间高度（本次 Chromium 46.8px / 完整 84.2px），随后正常完成；回到 system 时正确关闭这些位移动画。
- `verify-tactile.mjs` 的 23 组交互检查通过；94 组页面/尺寸/语言布局和 1 个后台设置流程通过；Android/iOS 微信引擎模拟的旋转、安全区、软键盘和草稿恢复均通过。
- 文案锁 43 模块、Vue/TypeScript 与正式构建通过；没有重新批准文案哈希，没有改变经营数据、原生成器或品牌素材。
- 证据保存在忽略目录 `artifacts/studio-runtime-fix/`；生产身份与公网原生浏览器复测结果见 `07_ops/STUDIO_VERIFICATION.md`。微信模拟不等同真机验证。

后续录屏和环境问题验收必须同时覆盖 `reducedMotion: null` 与真实滚动条。显式开启的演示环境只能作为演示，不能代表店主普通浏览器的默认状态。
