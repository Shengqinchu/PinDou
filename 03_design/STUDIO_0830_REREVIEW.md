# PinDou Studio 第二轮独立复审

复审对象：`e34120e42ed83cf374684efa1d1c4ab41b3e4412`。取证时间：2026-09-08 UTC（Hamilton 当地 9 月 7 日）。第一轮基线与证据均未覆盖。

## 结论

**核心功能修复与页面层级调整成立；最终交互验收仍保留，剩余是六项局部 P2 收尾，不需要再做一轮全站重构。**

原来的目录重试假零价、指标错筛、商品徽标拉伸和错误大字号均未复发。中文后台已真实使用 Sans SC；手机预约先看到实际选择，关闭状态有明确下一步；后台订单也不再被欢迎海报压到页面底部。主按钮 300ms 控制曲线和原生释放恢复有效，拼豆组装现在发生在可见父容器中。这些不是依据作者的测试数量判断，而是重新操作冻结运行版、观察截图、采样中间帧及核对代码所得。

仍需处理：触摸后的 hover 深色残留、后台内容与选中条不同步抵达、照片反向切换丢掉中间画面、点击当前菜单项不收起，以及中文孤行和错误/辅助文案。优先完成 N1–N4，再一并清理 N5–N6，最后做对应状态的窄复核即可。

本轮动态取证已结束，并已告知 PinDou 任务可以解除应用冻结开始局部修正。本报告的行号与判断只针对 `e34120e`，不自动批准随后修订，也不是部署或开放生产收款的指令。

## 范围与方法

- 对照：[第一轮报告](C:/Users/123/Desktop/PinDou/03_design/STUDIO_0830_REVIEW.md)、[实施响应](C:/Users/123/Desktop/PinDou/03_design/STUDIO_0830_RESPONSE.md)。实施响应作为待核实声明，而非验收证据。
- 实际检查本地 `http://127.0.0.1:5184/studio/` 与管理端，API 8011。生产仍是旧版，本轮没有部署。
- Chromium 实际浏览器操作、截图、逐帧采样、rendered-fonts；另用 Firefox 桌面和 Windows WebKit 手机尺寸复核商品与预约页。
- 商品尺寸独立检查 320、390、768、1080、1440、2048px；另外实看 320px 英文、390px 中文、1080×665 低高度等代表场景。不是声称所有页面在所有尺寸均完成全量验收。
- 网络失败、关闭营业状态采用浏览器路由模拟。QA 数据中的商品名、库存、订单和已开放状态只属于 QA，不当作真实经营事实。
- 未运行 `verify-desk-motion.mjs`，未 seed 数据、创单、支付、保存商品或修改生产参数。购物车测试只请求本地只读报价；草稿及开关仅在浏览器内修改并恢复。

## F01–F12 逐项判定

| 原编号 | 判定 | 本轮独立证据与说明 |
|---|---|---|
| F01 目录与时段恢复 | 通过 | 连续两次目录失败保持错误、没有套餐及零价；第三次恢复 3 套餐和 CA$16.00。再注入可用性失败，日期、2 人、180 分钟均保留，恢复合计 CA$48.00。ER02。 |
| F02 商品卡渲染 | 通过 | 六种宽度没有原来的竖条与大标题；标题 18px 桌面 / 16px 手机，徽标自然高度约 25–28.5px。Firefox/WebKit 复核一致。ER05、ER07。 |
| F03 指标下钻 | 通过 | 从待付款且含旧搜索条件进入“今日已收款”，实际请求变为 `status=received&day_kind=paid`，清掉旧搜索；新订单使用 created，待交付使用 confirmed。普通导航保留原筛选。ER02。 |
| F04 中文字体和层级 | 原项通过，仍有 N5 | 在真正显示的概览取到 `PinDou Sans SC / NotoSansSC-SemiBold`，不再是 SimSun；指标说明为 12px。实用页面标题简化，商品标题使用 UI 字体。残余中文孤行另见 N5。ER04、ER01。 |
| F05 手机预约顺序 | 通过 | 390px 首个套餐约 y=434，已经在首屏；关闭状态直接给店主联系方式和可展开价格，不再要求先走空选择器。手机首页照片也提前到约 y=468。ER01、ER07。 |
| F06 后台任务层级 | 通过 | 1440×900 最近订单区从旧版约 y=900 提前到 y=411；欢迎照片移除，已完成开店清单收拢，手机首先呈现当日指标。方向应保留，不再回到宣传页式后台。ER01。 |
| F07 控制节奏 | 部分通过 | 原生短按/长按不再有 180ms 锁存，主按钮与图标同用 300ms 控制曲线，reduced-motion 一致。但触摸颜色残留与切页节奏仍见 N1、N2。ER03。 |
| F08 拼豆编排 | 通过 | 父级先显现后组装；采样中有珠子处于显现/组装过程时，没有父级仍透明的帧。实际过程已可见，不是只改动画声明。ER03。 |
| F09 点击区与字段布局 | 原项通过，另有 N4 | 开关接收区真实为 44×44，点击轨道外但按钮内的上边缘可切换；手机中文名/英文名各占 350px 整行。原触控问题修正；新发现的当前菜单项边界另列 N4。ER05、ER06。 |
| F10 失败后的下一步 | 原项通过，仍有 N6 | 剪贴板拒绝后有提示与可选中微信号；小店失败可重新加载；到了购物车后 Toast 不再提供指向当前页的“去看看”。中文错误内容仍需收尾。ER02、ER05。 |
| F11 照片连续切换 | 部分通过 | 快速五连点最多两层，最终一层；下一张慢/失败时当前图片保留，失败有重试并可恢复。但中途反向切换仍直接丢层，见 N3。ER04。 |
| F12 样式职责 | 部分通过 | 商品、抽屉、开关等职责已经收拢，原商品选择器冲突消失。但 interactions.css 内仍保留旧的无条件 hover，实际造成 N1，不能仅因“移到一个文件”就算清理完。ER00、ER03。 |

F03 的日期口径另外核对了冻结后端：概览收款金额与列表付款日都使用 Hamilton 当日边界和 `paid_at`；收款状态包括已核实但需跟进订单。没有把下单日当付款日。此次未新增或 seed 跨日订单，跨日路径还采用源码及实施方已有单测作补充，不能表述成独立进行了真实跨日支付。

## 剩余问题：六项 P2

### N1 — 触屏已松开，按钮却继续保持 hover 深色

**类型：遗留状态错误；关联 F07/F12。Evidence：ER03 + ER00。**

在 `hover:false`、`pointer:coarse` 的手机环境点击关闭预约页的“复制店主微信”，500ms 后 `active=false`，但 `hover=true`，背景从 `rgb(165,88,66)` 变成 `rgb(127,65,51)` 并持续不恢复。另点空白才恢复。这不是已经删除的 `data-pressed` 锁存，而是旧 hover 颜色继续作用于触屏。

位置：[interactions.css:16](C:/Users/123/Desktop/PinDou/05_studio/src/styles/interactions.css:16)、`:19`、`:25` 的无能力条件 `.button:hover`、`.button-primary:hover`、`.button-outline:hover`；后面已有正确媒体条件内的规则。

**修正：**删除遗留无条件 hover，把 hover 样式限定于精细指针；保留原生 active 和已有 300ms 回程，不额外添加覆盖色或延迟锁存。验证正常复制与复制失败两条路径，松开后都回到应有状态。

截图：[点击后的颜色](C:/Users/123/Desktop/PinDou/artifacts/studio-0830-rereview/closed-390-after-tap.png)。

### N2 — 后台切页时，内容先到，选中条还在追

**类型：仍未解决的编排差异；关联 F07。Evidence：ER03 + ER00。**

从概览切到商品时，约 96.6ms，内容位移从 14px 只剩 1.616px，已推进约 88%；左侧选中条只移动约 25/156px，约 16%。因此新内容几乎已到位，而导航的视觉选中仍在途中。控制按钮曲线修对了，但整个工作区还保留前急后拖的运动。

位置：[motion.ts:37](C:/Users/123/Desktop/PinDou/05_studio/src/motion.ts:37) 的 `arrive()`，`:41` 的 14px/0.65 起点，`:46` 的 `studio-travel`；触发在 [CommerceManager.vue:139](C:/Users/123/Desktop/PinDou/05_studio/src/components/CommerceManager.vue:139)。

**修正：**优先让内容不做整块位移；若保留轻微位移，则与选中条采用协调的曲线和启动时刻。这里不要求照片和所有弹窗都用 300ms，也不建议再把所有控件一起延长。保留 v-show、草稿和滚动状态。

**验收：**概览→订单→商品反复切换，关注中间帧和操作感，而不是只检查两者最终时长都写成 300ms。

### N3 — 照片反向时直接消失的 incoming 层造成跳变

**类型：修复后的交互折衷；关联 F11。Evidence：ER04 + ER00。**

两层上限与预载/失败重试已经有效。残余问题是：在 `studio-11` 向 `journal-13` 淡入时，incoming 的 opacity 约 0.2558，点击上一张后，约 20ms 后这一层直接消失，回到完整旧图。它没有从当前透明度平滑退回，视觉上会跳一下。

位置：[PhotoViewer.vue:24](C:/Users/123/Desktop/PinDou/05_studio/src/components/PhotoViewer.vue:24) 的 `cancelSwap()`，`:33` 的 dominant-frame 阈值和 `:36` 清空 incoming；`:53` 在目标等于 current 时直接返回。

**修正：**反向回到当前底图时，将 incoming 从现有透明度淡出，再清理；连续切向其他图片可记录最新意图并中断到可连续的状态，不要每次丢掉当前合成画面。最多两层、保留当前图、预载与重试继续保留。不要为修平滑度回到旧版六层堆叠。

**验收：**在淡入约 25%、50%、75% 时反向，既不空白、不多层残影，也不跳回完整旧帧。连续输入可以合并为最新意图，不必排队逐张播放。

### N4 — 手机点击当前已选栏目，导航不关闭

**类型：本轮新发现的遗留边界，不冒充新引入的回归。Evidence：ER06 + ER00。**

在商品页打开手机菜单，再点击已经选中的“商品与体验”，菜单仍 `expanded=true`，背景仍 `inert=true`。用户必须另点关闭键或切其他栏目。正常切换到不同栏目能关闭，不代表这一分支正确。

位置：[CommerceManager.vue:125](C:/Users/123/Desktop/PinDou/05_studio/src/components/CommerceManager.vue:125) 的 `navigate()`，以及 `:139` 只在 `view` 变化时关闭菜单的 watcher。旧版也有相同逻辑，因此是此前漏测的交互边界。

**修正：**导航动作发生时就关闭手机菜单，即使目的地等于当前路由；复用现有菜单关闭后的焦点和滚动恢复。不要通过强制刷新或重挂载页面解决。

**验收：**当前栏目、其他栏目、Escape、关闭按钮各自测试。截图：[当前项仍保持展开](C:/Users/123/Desktop/PinDou/artifacts/studio-0830-rereview/desk-390-active-menu-stuck.png)。

### N5 — 精简后的中文介绍出现单字孤行

**类型：本次文案/行长调整后的排版细节；关联 F04 的后续打磨。Evidence：ER01 + ER00。**

1440px 首页介绍的第二行只剩“乐。”，1080×665 预约介绍也出现同样的尾行。字库已经正确，这次问题是行长与新文案没有一起验收。照片和主标题很完整，下面两字的孤行会明显拉低精细度。

位置：[Home.vue:167](C:/Users/123/Desktop/PinDou/05_studio/src/pages/Home.vue:167)、`:170` 的介绍和 [layout.css:31](C:/Users/123/Desktop/PinDou/05_studio/src/styles/layout.css:31) 的行长；预约页 `.visit-intro > p` 也要同查。

**修正：**调整这两段的文案、行长或末尾短语换行策略，形成自然的一行或均衡两行；不要缩小全局字号，也不要更换已验证的字库。中英分开验收。

截图：[首页孤行](C:/Users/123/Desktop/PinDou/artifacts/studio-0830-rereview/home-1440.png)、[低高度预约页](C:/Users/123/Desktop/PinDou/artifacts/studio-0830-rereview/visit-1080.png)。

### N6 — 中文错误态和辅助名称仍漏出英文内部表述

**类型：文案一致性；关联 F10。Evidence：ER02 + ER00。**

目录失败时 Visit/Shop 仍直接展示 `Failed to fetch`。Visit 已有可理解的中文标题和重试按钮，所以恢复功能通过；Shop 则几乎只有原始异常和重试链接。订单内容筛选的中文可见标签是“内容”，显式 `aria-label` 却仍是 `Order type`。

位置：[Shop.vue:43](C:/Users/123/Desktop/PinDou/05_studio/src/pages/Shop.vue:43)、[Visit.vue:148](C:/Users/123/Desktop/PinDou/05_studio/src/pages/Visit.vue:148) 的异常直接赋值；[OrdersPanel.vue:199](C:/Users/123/Desktop/PinDou/05_studio/src/components/admin/OrdersPanel.vue:199) 的固定英文 aria-label。

**修正：**把网络不可达/超时映射为当前语言的可理解提示，原始异常留在开发诊断中；不要吞掉服务端有意义的业务错误。aria-label 使用现有双语函数，或移除冗余英文属性，让原生本地化 label 提供名称。复制失败后的手动复制方案和真实重试入口保留。

## 设计判断：哪些应保留

- **首页继续承担邀请与实拍展示。**照片更早进入手机视野，英文字体、纸色和照片关系无需重做；只修 N5 的具体断行，不扩大成新一轮字体方案。
- **预约页已经像操作页。**短标题、套餐、日期与关闭状态顺序成立。QA 中超长的测试套餐名不当作生产宣传文案；可继续在边界测试里验证，不因此虚构新套餐。
- **后台已经像工作台。**欢迎照片被移除，最近订单提前，说明字号提升；不再要求换布局语言或复制 T-Check 蓝白配色。
- **基础微交互已大幅接近目标。**300ms 控制、原生短按、拼豆可见性均可保留；目前最需要的是 N1–N3 的状态连续性，而不是更多装饰运动。
- **照片失败状态有实用性。**慢/失败时保留当前图片，错误提示与重试位置明确。截图：[照片失败而当前图保留](C:/Users/123/Desktop/PinDou/artifacts/studio-0830-rereview/home-1440-photo-failed.png)。

## 保留行为与验收边界

商品草稿关闭后跨订单/商品面板仍保留；抽屉 Escape 关闭后焦点回到商品行，body 恢复 static。开关外圈点击有效，修改仅存在于未保存草稿。购物车通知不再有当前页自链接；切换语言后填写的称呼仍保留。主按钮与图标 reduced-motion 一致为 `none`/`0s`。这些行为没有因为此次修正而回退。

真实 iOS Safari、iOS 微信、Android 微信仍未测试。Windows WebKit、手机尺寸和触摸模拟不是微信真机证明。本轮也没有验证真实收款、退款或生产履约；QA 数量和金额不用于推断生产经营情况。

## 收尾路径与下一次复核

1. **状态修正路径：**依据 ER03/ER04/ER06 修 N1–N4。删除旧 hover；协调一次切页的动画；保留照片反向中间状态；当前菜单项也走正常关闭。无需改交易规则。
2. **文字路径：**依据 ER01/ER02 修 N5–N6。只调整已指出的中文行长、用户错误提示和辅助名称。
3. **窄复核：**提交新 SHA、上述六项处理说明，以及触摸松开/切页中间帧/照片反向/当前菜单项/两段中文/失败重试截图。保留有效的草稿、焦点、滚动和 reduced-motion 回归，不重复进行全站视觉重构。

## 独立证据索引

所有新证据在 `C:/Users/123/Desktop/PinDou/artifacts/studio-0830-rereview/`。第一轮目录保持不变。ER00 是冻结 Git 树，其余为本轮浏览器产物。

| Evidence | 内容 | 文件 |
|---|---|---|
| ER00 | 静态因果与日期口径 | `e34120e` Git 树；正文源码链接行号以该版本为准 |
| ER01 | 实际页面截图、DOM、尺寸与可见控件 | [browser-evidence.json](C:/Users/123/Desktop/PinDou/artifacts/studio-0830-rereview/browser-evidence.json) 及正文截图 |
| ER02 | 连续目录失败恢复、时段恢复、指标意图、普通导航、复制和目录重试 | [functional.json](C:/Users/123/Desktop/PinDou/artifacts/studio-0830-rereview/functional.json) |
| ER03 | 控制/切页帧、触摸 hover、拼豆帧、降动效 | [motion-fonts.json](C:/Users/123/Desktop/PinDou/artifacts/studio-0830-rereview/motion-fonts.json) |
| ER04 | 照片层数、延迟/失败恢复、反向中断、可见后台 rendered-fonts | [photo-controls.json](C:/Users/123/Desktop/PinDou/artifacts/studio-0830-rereview/photo-controls.json) |
| ER05 | 开关实际命中、整行名称、草稿/模态恢复、六宽度商品、购物车/语言 | [final-checks.json](C:/Users/123/Desktop/PinDou/artifacts/studio-0830-rereview/final-checks.json) |
| ER06 | 当前栏目不关闭的现场状态 | [active-menu.json](C:/Users/123/Desktop/PinDou/artifacts/studio-0830-rereview/active-menu.json) |
| ER07 | Firefox / WebKit 商品和预约页复核 | [cross-engine.json](C:/Users/123/Desktop/PinDou/artifacts/studio-0830-rereview/cross-engine.json) |
| ER08 | 没有尝试创单/保存等写请求 | [blocked-mutations.json](C:/Users/123/Desktop/PinDou/artifacts/studio-0830-rereview/blocked-mutations.json)，内容为 `[]` |

ER03 中第一次桌面字体查询命中了 v-show 隐藏区域，`fonts=[]` **不作为字体失败或通过的依据**。字体结论使用 ER04 的 `deskFonts`：真实显示 overview 时，标题与指标说明均获取到自带 Sans SC 字形。照片/草稿脚本中曾修正一个未限定已打开 dialog 的定位器；该定位器错误没有算成应用缺陷。随后遇到的当前菜单项未关闭，则经实际现场与源码确认，单独列为 N4。

上述 JSON 的 SHA-256：

```text
browser-evidence.json   6811f7f2318a4fcbbeabb49822be519dbddf0e66736e9974a20737b6a9c810f3
functional.json         ce76a40096d96e3d870130e6d1056035d347c80d22f4f491121cb5c32159df95
motion-fonts.json       319961ddc40f82b2c97249f41e4e83feca965121a34b5dbd0121f02208fecbe7
photo-controls.json     76df37f6b42387f5006da1cf211950e108746f133398e93450d037bf41d2d91f
final-checks.json       4a10f54e138355fe23a49c33cab67f9c965568d9560f9c55ae890456adb2bd06
active-menu.json        2538d6b463e05a23987f60223ffd390395c537a11621216e29cd22fdbe71495d
cross-engine.json       de4ace77791dca6a96378b72d97b2c594671e32abdae66e45ffc614ec08ba140
blocked-mutations.json  4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945
```

离线复核示例，不写服务器或 QA 数据：

```powershell
git -C 'C:\Users\123\Desktop\PinDou' show 'e34120e:05_studio/src/components/PhotoViewer.vue'
Get-Content -Raw 'C:\Users\123\Desktop\PinDou\artifacts\studio-0830-rereview\photo-controls.json'
Get-FileHash -Algorithm SHA256 'C:\Users\123\Desktop\PinDou\artifacts\studio-0830-rereview\photo-controls.json'
```

复现辅助脚本也保留在新证据目录，依赖 `driver.cjs` 的浏览器上下文；它们不是可直接对生产执行的支付测试。后续证据请另存目录，不覆盖本轮快照。

## 复审自检

- [x] F01–F12 均有明确判定，没有以作者测试数量替代验收。
- [x] 剩余问题均关联冻结源码和独立动态证据，区分遗留边界、修复后的折衷与文案细节。
- [x] 保留有效实现，给出有限的局部收尾路径。
- [x] 未修改应用源码、seed QA、保存商品、创单、支付或部署；浏览器会话已关闭。
- [x] 真机微信、真实支付与生产经营结论明确留在本轮范围之外。
