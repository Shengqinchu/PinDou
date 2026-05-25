# PinDou 拼豆小程序 — 全局共用组件概览 (Components Overview)

本文档归纳整理了由 Claude Design 设计并实现在 `03_design/wireframes/shared/components.css` 中的共用组件，旨在帮助前端开发人员理清组件的 BEM 变体结构、推荐使用场景及 HTML 写法。

---

## 目录
1. [手机外壳框架 (Phone Frame Chrome)](#1-手机外壳框架-phone-frame-chrome)
2. [按钮组件 (Buttons)](#2-按钮组件-buttons)
3. [卡片容器 (Cards)](#3-卡片容器-cards)
4. [图标药丸 (Chips)](#4-图标药丸-chips)
5. [状态标签 (Tags & Badges)](#5-状态标签-tags--badges)
6. [底部导航栏 (Tab Bar)](#6-底部导航栏-tab-bar)
7. [辅助小工具 & 链接 (Utility Helpers & Links)](#7-辅助小工具--links)

---

## 1. 手机外壳框架 (Phone Frame Chrome)
在 HTML 设计原稿中，`.frame` 组件用于在 PC 浏览器中模拟 375x667 尺寸的微信小程序真机视口，并注入系统状态栏及原生胶囊。
- **uni-app 实现转换**：在转换为 uni-app 时，该组件被抽象为全局 Layout 包裹组件 `<MiniProgramLayout>`。

### 变体与子元素
- `.frame`：视口主容器（375x667，圆角 36px，高保真模拟发光阴影）。
- `.frame__status`：系统状态栏（高度 20px，显示时间及网络、电池图标）。
- `.frame__header`：微信小程序顶部 NavigationBar 导航栏（高度 44px）。
  - `.frame__header--home`：首页专用导航栏，左对齐，去除返回键，间距微调。
- `.frame__logo` / `.frame__logo-dot`：PinDou 品牌标徽。
- `.frame__back`：返回按钮（返回上一页 `<a href="..." class="frame__back">`）。
- `.frame__title`：页面标题，绝对定位居中。
- `.frame__capsule`：高保真模拟微信胶囊菜单（`⋯` 与 `×` 按钮）。
- `.frame__body`：内容区域（高度 `603px`，撑满剩余视口）。
  - `.frame__body--scroll`：支持纵向滚动的页面主内容区。

---

## 2. 按钮组件 (Buttons)
所有的按钮采用高圆角（`border-radius: 24px`），支持多种主题和尺寸级别，并带有轻微的交互缩放动效 (`scale(0.97)`)。

### 2.1 主题变体 (Themes)
- `.btn--primary`：主推付费 CTA，使用粉-橙-桃三色高饱和渐变背景，带有柔和的发光阴影 (`--pd-shadow-cta`)。**用于引导用户购买、升级、兑换等高价值行为**。
- `.btn--secondary`：次要按钮，无背景色，配合圆润的细边框。**用于次要操作或取消操作**。
- `.btn--ghost`：幽灵按钮，浅粉背景 (`--pd-pink-50`)，深粉色文本。**用于轻量级交互、重试、或者切换风格等操作**。
- `.btn--pink`：单色纯粉按钮 (`--pd-pink`)。**在免费功能路径中充当主要 CTA（如“下载免费图纸”），以和高溢价的渐变金/橙色 Primary 按钮区分开来**。
- `.btn--success`：绿色成功按钮 (`--pd-success`)。**在 CDK 兑换成功或支付确认等正面流程的反馈页面使用**。

### 2.2 尺寸与布局变体 (Sizes)
- `.btn--block`：宽度 100% 撑满。
- `.btn--lg`：高度 54px，字号 17px，带有字间距，视觉冲击感强，适合页面级底部 CTA。
- `.btn--md`：高度 50px，通用基础尺寸。
- `.btn--sm`：高度 38px，padding 两侧缩窄，适合卡片内或局部的操作按钮。

### HTML 结构示例
```html
<!-- 渐变色主 Block 按钮 -->
<button class="btn btn--primary btn--lg btn--block">
  <span>AI 生成精品图纸 (9.9元)</span>
  <svg>...</svg> <!-- 支持带前置/后置图标 -->
</button>

<!-- 纯粉色中等次按钮 -->
<button class="btn btn--pink btn--md">免费下载</button>
```

---

## 3. 卡片容器 (Cards)
作为卡片式布局的小程序，所有的信息和功能切片都装在 `.card` 容器中。

### 变体与子元素
- `.card` / `.pd-card`：基础卡片（白色背景，圆角 16px，柔和粉褐色微阴影 `--pd-shadow-card`）。
- `.card--recommended`：**明星推荐卡片**。使用 `border-box` 和 `padding-box` 的双重背景描边技巧，呈现 **2px 极致渐变边框**，并外加较强的高光投影 (`--pd-shadow-float`)。**常用于套餐资费对比、上传后的 AI 路径精品生成推荐卡**。

### HTML 结构示例
```html
<div class="card card--recommended">
  <div class="card__badge">推荐</div>
  <h3 class="card__title">AI 路径精品生成</h3>
  <p>让 AI 为您设计 Q 版拼豆图纸，细节更饱满。</p>
</div>
```

---

## 4. 图标药丸 (Chips)
药丸组件用于展示轻量级属性、标签或者可点击的小过滤器。
- `.chip`：圆形胶囊背景，带细边框和微弱阴影。
- `.chip__icon`：粉色前置图标（如小星星、火苗等）。

### HTML 结构示例
```html
<div class="chip">
  <span class="chip__icon">✨</span>
  <span>首次免费体验</span>
</div>
```

---

## 5. 状态标签 (Tags & Badges)
比药丸更精简，主要用于信息分类、打标或者在卡片右上角提示角标。

### 变体
- `.tag`：默认灰色背景小标签，圆角 6px。
- `.tag--ai`：**AI 标识特制版**。采用温暖的渐变色背景，高圆角。**用于满足合规性要求的 FinishedPreview 以及分享卡片，醒目标注 "AI 辅助"**。
- `.tag--recommended`：明星主推角标，粉橙渐变背景，带有强发光。**用于价格卡、功能卡上吸引用户点击**。
- `.tag--warm`：浅橘色背景标签。

### HTML 结构示例
```html
<span class="tag tag--ai">AI 辅助生成</span>
```

---

## 6. 底部导航栏 (Tab Bar)
在主路径页面的最底部提供页面切换。在 uni-app 转微信小程序后，此组件的布局可以转为原生 TabBar 或在全局 Layout 自定义组件中调用。

### 变体与子元素
- `.tabbar`：底部栏容器（微粉微橙乳白半透明模糊背景，带有毛玻璃高斯模糊，通过 border-top 细线分隔）。
- `.tabbar__item`：单个 Tab 按钮。
  - `.tabbar__item--active`：激活态（文本及图标呈现粉色 `--pd-pink` 状态）。
- `.tabbar__icon`：图标容器。
  - `.tabbar__icon--outline`：未激活状态展示的细线图标。
  - `.tabbar__icon--filled`：激活状态展示的实心图标。
- `.tabbar__label`：下方的小文字，激活态字重为 600。

---

## 7. 辅助小工具 & 链接 (Utility Helpers & Links)
- `.footnote`：法律免责或细则微缩文本。**字体极小 (11px)，行高舒适，文本呈淡灰色 (`--pd-fg-3`)，居中排版**。多用于用户同意书前置和底部合规性文案。
- `.help-link`：帮助链接。内置一个底部带有下划线的文字标签 `.help-link__label`，以及粉色的前置问号或说明图标。
- `.text-grad`：**渐变文本渲染工具**。通过 `-webkit-background-clip: text` 使得任意普通标题、数字或高亮文本呈现主色渐变，**适合渲染 9.9、28 元等付费导流数字**。
