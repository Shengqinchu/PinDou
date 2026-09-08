# 模块浮起与按压反馈：代码对照和修正

2026-09-08。对应店主本次要求：参考 Turnitin 模块“缓缓浮起”、按钮“缓慢弹跳”，从实际代码改善客户端和管理员后台，保留既有文案。

## 实际参考与发现

本次在只读的 `C:/Users/123/Desktop/Turnitin_generation` 读取并运行 `admin-dashboard/index.html?ui-preview=shell` 的现有本地预览入口，未登录或改动其生产服务。参考仓库当时 HEAD 为 `067008cfbd869cd548c78532ad269837cb01f97e`。主要依据：

- `admin-dashboard/index.html` 的 `#help-card`，以及浏览器执行 Tailwind 后的计算样式。
- `admin-dashboard/css/index.css` 的 `T-CHECK CARD MOTION CONTRACT`、`.task-action-button` 和 `--press-shadow`。
- `docs/FRONTEND_INTERACTION_AND_MOTION_STANDARD.md`，作为约束和验收方法参考；与实际运行不同之处单独核对。

| 问题 | 修改前实际测量 | 修正 |
|---|---|---|
| 日记卡片没有整体反馈 | `.journal-story-link` 的 transition 为 0s，悬停/按下位移均为 0 | 卡片接入 4px 浮起；照片外壳承担阴影，避免整篇图文变成带框面板 |
| 当前后台预约控件漏接旧样式 | `.reservation-desk-metrics > button` 只过渡背景/边框；`.reservation-desk-days button` 是 0s，二者位移均为 0 | 当前统计卡片和日期按钮接入同一状态契约 |
| 只照抄文档的曲线 | 本站原曲线为 `.42,0,.58,1`；Turnitin 帮助模块实际是 Tailwind 的 `.4,0,.2,1` | 统一采用实测模块曲线，保留 300ms；CSS、GSAP 状态和按压一致 |
| 按钮缺少厚度 | 原主按钮仅 3% 模糊阴影，按压依赖轻微缩放 | 加入 3px 实色底边，悬停 4px，按压底边归零，搭配柔和投影 |
| 普通短按不明显 | 旧检查只判断 45ms 点击后是否仍 active，没有验证回弹中间帧 | 为短按增加一个可替换的 300ms 反馈；采样确认下沉和回升均存在 |
| 客户端与后台样式加载顺序可变 | `desk.css` 随 Manage 页面延迟注入 | 统一在 main.ts 导入组件样式，最后加载 tactile.css；页面来回切换不再改变覆盖顺序 |

参考站也有需要避免的旧实现：报告按钮 `.task-action-button:hover` 在 `:active` 后且同级优先，实测鼠标按下仍保持悬停的 -1px。本站明确把 active 放在 hover 后，并测试二者同时匹配，未照搬该顺序问题。

## 当前实现

- `src/styles/tactile.css` 是客户和后台控件的最终状态契约。模块浮起 4px，主/次按钮浮起 2px，紧凑日期/图标控件浮起 1px。纯说明内容不增加点击行为。
- 主/次按钮按下移至 +3px、轻微缩至 .988；底边收拢。按钮文字与图标随同一物理按钮运动；旋转中的加载图标保持其业务状态。
- `src/motion.ts` 统一 `300ms cubic-bezier(.4,0,.2,1)`，现有叙事入场与弹层的独立时长保留。相关 CSS fallback 同步更新。
- `src/press.ts` 使用原生 Web Animations 为普通短按补全回弹。CSS 继续负责悬停和持续按压，指针/键盘释放后短按反馈总长 300ms，每个元素最多一个反馈效果。再次按下、移出或重新进入时从当前画面接续，禁止叠加队列。
- 点击、路由、表单提交均按原生事件立即执行；没有拦截默认事件、没有等待动画的业务计时器，也没有延迟松开 `.pressed` 一类状态。出现 disabled、inert、DOM 移除、页面隐藏、窗口失焦或降动效变化时清理反馈。
- 触摸移动超过阈值即放弃点击反馈，遵循原生滚动。键盘 Space/Enter 可使用；`prefers-reduced-motion` 下位移及回弹关闭，聚焦和状态仍可读。
- 触摸松手自动产生的 `pointerout` 不当作鼠标移走处理，否则短按反馈会被提前取消。最终测试同时断言触屏按钮达到约 +3px、触屏卡片达到约 +1px，并回到 0；不能只检查“没有残留”。
- 头像、平台图标、日记原文、品牌字标与 43 个批准内容模块未改；购物和预约业务规则未改。

普通 CSS 过渡在反向播放时可能缩短剩余时长，见 [CSS Transitions 的反向过渡规则](https://www.w3.org/TR/css-transitions-1/#reversing)。本次短按反馈的创建/中断使用 [Element.animate](https://developer.mozilla.org/en-US/docs/Web/API/Element/animate) 与 [Animation.cancel](https://developer.mozilla.org/en-US/docs/Web/API/Animation/cancel)，仅作用于视觉，不代替事件和业务状态。

## 验证与证据

- `npm run build`：文案锁定 43 模块、Vue/TypeScript 和正式构建通过；批准哈希未重新生成。
- `node scripts/verify-tactile.mjs`：Chromium、Firefox、WebKit，共 23 组结果。覆盖实际页面中的悬停、持续按压、45ms 短按、连续输入中断、移出回零、禁用、键盘、降动效和触屏菜单。
- `node scripts/verify-vision2.mjs`：94 组页面/尺寸/语言布局检查和 1 个后台设置流程，共 95 项通过；仅使用隔离 QA 数据库。
- `node scripts/verify-vision2-motion.mjs`：实际中文字体为 PinDou Sans SC；套餐价格展开中间高度约 74.7px / 完整内容 132.5px，连续切换保持内容正确。
- `node scripts/verify-vision2-webview.mjs`：Android 微信 UA/Chromium、iOS 微信 UA/WebKit 两组通过，包括旋转、安全区、软键盘视口、语言切换、版本更新和草稿保留。这是模拟，不代表真机验收。
- 独立嵌套采样：设置卡片 -4px、内部按钮 -2px，11 个中间帧进度差小于 .06；按钮图标与按钮整体同步。
- Chromium 真实触摸事件模拟：从按钮上向上滑动，页面滚动 125px，点击数 0，剩余反馈动画 0。

证据目录为忽略路径 `artifacts/studio-tactile/`：`before.json`（包括 Turnitin 运行结果）、`verification.json`、`synchronization-and-scroll.json`、截图及实际界面录屏。旧 `after-frames.json` 是开发中间结果；最终状态以 `verification.json` 为准。发布身份记录于 `07_ops/STUDIO_VERIFICATION.md`。

后续新增模块应在真实页面上检查 hover/active/focus/disabled 和短按中间帧，不得用写了 transition、测试没有报错或静态截图替代实际交互验证。
