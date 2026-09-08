# PinDou Studio 独立审查：先修正确性，再重建视觉主次与动效节奏

审查人：最新项目0830。取证日期：2026-09-07。本文是第一轮审查与返工清单，不是设计验收通过记录。

## 结论与范围

当前问题不只是“动画不够慢”：有实际 CSS 渲染错误、错误恢复后的虚假零价、指标跳转语义错误，也有营销页、预约表单、后台工作台使用了过于相似的视觉节奏。主按钮与图标已经同步，弹窗焦点和草稿保留也有有效实现；不应把这些推倒重写。下一轮应先修下面的功能与渲染问题，再调整中文层级、页面密度和运动曲线。增加动画数量或统一拉长时长，不能解决这些问题。

- 授权与任务依据：[STUDIO_0830_HANDOFF.md](C:/Users/123/Desktop/PinDou/03_design/STUDIO_0830_HANDOFF.md)。本轮只检查与写审查文档，不修改应用源码、不部署、不修改真实营业设置或订单。
- 应用基线：`edaa3f8`；取证时仓库 HEAD 为 `8ac08a77f2b4b864ffc509f7ef409daba58f1058`。下列源码行号全部指向这一冻结实现，不混入返工后的行号。
- 线上：[工作室网站](https://pindoupuppy.com/studio/)，资源 `index-DPHaiLyV.js`；交接发布编号 `20260907232410-studio-v1`。
- 本地 QA：`http://127.0.0.1:5184/studio/`，后端 8011。QA 的可用时段、库存和收款就绪状态不是生产事实。
- 当前生产购买关闭、营业时间/容量/税务尚未确定，是明确的业务状态，不作为服务故障。本次没有支付、创单、变更库存或保存后台表单；仅请求本地只读报价，并在浏览器内修改未保存草稿。
- 证据在 `C:/Users/123/Desktop/PinDou/artifacts/studio-0830-review/`。原应用取证已完成，最高优先级清单已回传 PinDou 任务；后续实施由该任务负责。

## 优先级总表

P1 表示下一轮应优先修正；P2 表示随后完善。这里的优先级是产品审查顺序，不是安全漏洞评级。

| 编号 | 优先级 / 类型 | 已观察的问题 | 下一步 |
|---|---|---|---|
| F01 | P1 / 功能 | 商品目录失败后，重试出现 0 套餐、21 个时段和 `CA$0.00` | 完整恢复目录与时段，区分未知价格和零价 |
| F02 | P1 / 渲染 | 商品状态变长竖条；商品标题误用 46px / 31px 大标题 | 修正定位约束和 `.product-card` 选择器 |
| F03 | P1 / 功能 | 点“今日已收款”仍保留“待付款”筛选 | 指标携带明确的筛选上下文 |
| F04 | P1 / 中文排版 | 后台标题实际回退 SimSun；大量操作说明仅 9–11px | 明确中文字体角色，提高操作层级 |
| F05 | P1 / 用户流程 | 手机预约先看一屏宣传；未开放提示在全部控件之后 | 先展示可预约状态，再提供实际选择 |
| F06 | P1 / 后台密度 | 欢迎区、照片、已完成开店清单压过当日运营信息 | 改成任务优先的工作台 |
| F07 | P1 / 动效设计 | 480ms 曲线前急后拖；短按后仍继续下压 | 用已验收曲线作对照，分开控制与叙事节奏 |
| F08 | P1 / 动效编排 | 拼豆组装大半发生在透明父容器中 | 可见后再组装，纳入同一时间轴 |
| F09 | P2 / 触控 | 后台语言按钮 14×30、开关 44×26 | 扩大真实点击区，不只增大视觉图标 |
| F10 | P2 / 异常反馈 | 复制微信失败无提示；小店加载错误无重试入口 | 给失败后的实际下一步 |
| F11 | P2 / 照片交互 | 连点翻页最多叠 6 张图，产生多重残影 | 保留稳定舞台，限制旧图堆叠 |
| F12 | P1 / 实现治理 | 组件样式与旧选择器分散在多层 CSS，已经造成 F02/F04 | 在返工同时收拢职责，不再末尾叠覆盖 |

## 逐项发现与可实施修正

### F01 — “重试成功”后仍缺目录，并把未知价格显示为零

**Evidence：E00、E05。状态：已复现；置信度高。**

在本地 QA 仅让第一次 `/catalog` 请求失败。进入预约页后点击“重试”，实际只请求可用时段，没有重新请求目录。结果为 `plans=0`、`slots=21`、`catalogRequests=1`、错误消失，合计显示 `CA$0.00`。这是受控故障注入，不是声称生产正在发生目录故障。截图：[重试后的错误状态](C:/Users/123/Desktop/PinDou/artifacts/studio-0830-review/qa-catalog-failure-after.png)。

位置：[Visit.vue:52](C:/Users/123/Desktop/PinDou/05_studio/src/pages/Visit.vue:52) 的 `price_cents || 0`，以及 [Visit.vue:96](C:/Users/123/Desktop/PinDou/05_studio/src/pages/Visit.vue:96) 的初始化和 [Visit.vue:342](C:/Users/123/Desktop/PinDou/05_studio/src/pages/Visit.vue:342) 的重试按钮。

**影响：**页面看似恢复，却没有套餐价格。用户会把零元当成报价，后续购物车的真实报价与前页矛盾。这比动画问题更应先修。

**改法：**建立完整的初始化/恢复入口，先确保目录可用，再恢复时段；单独区分目录、可用性和报价状态。未知金额显示“正在获取价格”或可重试的错误，不能用 `0` 兜底。保留用户已经填写的日期、人数和时长；数据恢复不应要求重填。

**验收：**分别注入目录失败、可用性失败和一次超时；重试后套餐、价格、时段一致。若目录仍失败，不能清掉错误后展示零价。对应 owner frontend 的显式状态模型、网络错误重试，以及 T-Check 的“状态可读”。

### F02 — 小店商品卡存在两个可见的 CSS 错误

**Evidence：E00、E01、E02、E06。状态：已复现；置信度高。**

“即将上架”不是普通小徽标，而是贯穿图片的长竖条。原因是 [style.css:1130](C:/Users/123/Desktop/PinDou/05_studio/src/style.css:1130) 的 `.product-image > span` 设置 `bottom:13px`，而 [commerce.css:188](C:/Users/123/Desktop/PinDou/05_studio/src/styles/commerce.css:188) 又给 `.product-status` 设置 `top:14px`，上下约束同时生效。桌面 Firefox 实测高度约 358.6px；390px WebKit 仍有 160.5px。

商品标题的真实字号是桌面 46.08px、手机 31px。模板 [Shop.vue:87](C:/Users/123/Desktop/PinDou/05_studio/src/pages/Shop.vue:87) 使用 `.product-card`，但小标题规则仍是 [style.css:1145](C:/Users/123/Desktop/PinDou/05_studio/src/style.css:1145)、[typography.css:82](C:/Users/123/Desktop/PinDou/05_studio/src/styles/typography.css:82) 和 `:193` 的 `.product h2`，所以根本没有命中。

截图：[桌面商品卡](C:/Users/123/Desktop/PinDou/artifacts/studio-0830-review/live-shop-1440-products.png)、[手机商品卡](C:/Users/123/Desktop/PinDou/artifacts/studio-0830-review/live-shop-390-viewport.png)、[WebKit 复核](C:/Users/123/Desktop/PinDou/artifacts/studio-0830-review/webkit-shop.png)。

**改法：**让商品组件拥有唯一的名称、标题、状态、价格规则，清理过期 `.product` 选择器。徽标只选择一个垂直锚点，显式取消相反方向约束；不要只追加一个仍会输给旧选择器的 `bottom:auto`。商品标题回到 UI 正文体系，建议桌面 17–18px、手机 16px，保留足够行高，不再使用宣传区块级宋体大标题。

**验收：**中英、上架/待上架、320/390/768/1440px 同时检查；徽标保持自然高度，标题与价格可扫描。`scrollWidth` 正常不等于商品卡正确。对应 T-Check 的字号角色和组件完整状态原则。

### F03 — 概览指标没有真正下钻到对应订单

**Evidence：E00、E05。状态：已复现；置信度高。**

复现路径：订单管理选“待付款” → 今日概览 → 点“今日已收款” → 回到订单页后，选中筛选仍是“待付款”。截图：[指标与筛选不一致](C:/Users/123/Desktop/PinDou/artifacts/studio-0830-review/qa-desk-390-metric-drilldown.png)。

位置：[OverviewPanel.vue:87](C:/Users/123/Desktop/PinDou/05_studio/src/components/admin/OverviewPanel.vue:87)、`:95`、`:105` 都只传 `navigate('orders')`；[CommerceManager.vue:125](C:/Users/123/Desktop/PinDou/05_studio/src/components/CommerceManager.vue:125) 只切换工作区。

**改法：**区分普通导航与带条件下钻。普通导航继续保留筛选、滚动与表单；指标点击应携带明确意图，例如 Hamilton 当日创建、当日核实收款、待交付或需跟进。列表中显示该筛选及“清除筛选”。先对齐指标的时间字段，再实现过滤，不能把“今日收款”误当“今日创建的已付款订单”。

**验收：**先设置任意旧筛选，再逐个点击指标，列表含义必须与指标一致；返回普通导航仍能保留合理状态。对应 owner admin 的“异常指标跳转对应列表”，不是简单跳到某个页面就算完成。

### F04 — 中文字体职责不稳定，信息字号却过小

**Evidence：E00、E01、E02、E05。字体回退已复现；字号调整为设计建议。**

后台欢迎标题实际渲染的是系统 **SimSun**。这不是凭肉眼判断：Chromium 的 rendered-fonts 结果是 `isCustomFont=false`，而正文使用的是项目自带 `PinDou Sans SC / NotoSansSC`。原因在 [desk.css:258](C:/Users/123/Desktop/PinDou/05_studio/src/styles/desk.css:258)：`.desk-welcome h1` 改为 `var(--display)`，该变量只有英文字体和通用 serif，没有中文项目字体。

同时，后台指标说明桌面只有 10px，手机降到 9px；英文/中文切换按钮为 11px。位置：[desk.css:322](C:/Users/123/Desktop/PinDou/05_studio/src/styles/desk.css:322)、`:343`、`:1941`、`:1964`。这里不仅是状态短徽标，还承载“按 Hamilton 当地日期统计”“已付款确认的座位”等解释。

**改法：**保留用户认可的 DM Serif Display / Outfit 英文字体。中文宣传标题可以少量使用 Serif SC，操作页与后台统一使用明确的 Sans SC 字体栈；不要用 `--display` 去承担中文回退。关键表单/动作文字建议 14–16px，说明 12–13px，9–10px 只用于极短的非关键标签。先删重复说明、重新分组，再调整布局，不能继续把字缩小。

**审美判断：**首页的双色双行标题可以保留作为一个主视觉，但不应在小店、购物车、预约页、后台反复使用同样的“诗句 + 红色第二行”来替代信息层级。中文高密度字形与英文斜体的视觉重量不同，需要独立排版，不能只替换字符串。

**验收：**检查实际 rendered fonts，不只检查 `font-family` 字符串；检查 390px 和低高度桌面。Windows 字体正确不自动证明 iOS 微信字体正确。对应 T-Check“可读优先”，以及 PinDou 的双语字体角色。

### F05 — 手机预约页把宣传内容放在任务前，关闭状态出现太晚

**Evidence：E00、E01、E04。状态位置已复现；重排为设计建议。**

390×844 首屏先展示双行大标题、介绍、235px 照片、地址，再开始步骤条；首个套餐选择在首屏外。选择日期、人数、时长之后，才看到“新的到店时段，正在安排中”。下方仍展示金额和禁用“加入购物车”，却没有方便的下一步。截图：[进入预约页](C:/Users/123/Desktop/PinDou/artifacts/studio-0830-review/live-visit-390-viewport.png)、[关闭状态](C:/Users/123/Desktop/PinDou/artifacts/studio-0830-review/live-visit-390-closed-state.png)。

位置：[Visit.vue:124](C:/Users/123/Desktop/PinDou/05_studio/src/pages/Visit.vue:124) 先渲染完整 `.booking-story`，`:172` 才到表单；[layout.css:191](C:/Users/123/Desktop/PinDou/05_studio/src/styles/layout.css:191) 只是把双栏改成单栏；[Visit.vue:307](C:/Users/123/Desktop/PinDou/05_studio/src/pages/Visit.vue:307) 将关闭状态放在选择器之后。

**改法：**手机先给简短标题与是否开放，再进入体验、日期、时段；空间照片和详细到店介绍后置或可展开。日期快捷条可以保留，但完整日期输入可作为“其他日期”，减少连续重复控件。把“尚未开放”与“这一天已无时段”区别放在用户开始选择之前；提供真实可执行的“看看空间/复制微信咨询”入口，不承诺未建立的自动通知或人工确认流程。

首页也应与预约页区分：手机首页照片约从 y=545 才开始，前面已经有公告、双语标志、两行标题、介绍、两个动作、拼豆装饰和脚注。可缩短介绍、减少装饰层，提前看到真实桌面与作品；预约页则直接服务选择与结账。不是要求所有页面都塞满首屏。

**验收：**390px 的首次查看能立即理解能否预约以及下一步；已配置 QA 能顺利走到购物车；生产关闭状态保持真实，不能为了视觉顺畅而虚构时段、价格或库存。对应 PinDou“邀请页与实用表单必须有不同密度”。

### F06 — 后台仍像第二张营销落地页

**Evidence：E00、E01、E04。布局事实已确认；优先级取舍为设计判断。**

1440×1000 下，欢迎文案与照片占用上方约 220px，之后是四张指标卡和两张大面板，最近订单约到 y=900 才出现。即使 QA 已完成开店设置，完整“开店准备”清单仍常驻。手机上还保留 95×155px 的窄照片，关键说明却缩成 9px。截图：[桌面概览](C:/Users/123/Desktop/PinDou/artifacts/studio-0830-review/local-desk-1440-viewport.png)、[手机概览](C:/Users/123/Desktop/PinDou/artifacts/studio-0830-review/local-desk-390-viewport.png)。

位置：[OverviewPanel.vue:46](C:/Users/123/Desktop/PinDou/05_studio/src/components/admin/OverviewPanel.vue:46)、`:184`、`:221`；[desk.css:251](C:/Users/123/Desktop/PinDou/05_studio/src/styles/desk.css:251) 及 `:1925`。

**改法：**欢迎缩为日期、营业状态和短标题；照片留给公共网站。设置未完成时突出具体缺项，完成后收拢成简短状态条。概览优先展示今日到店、待交付、需跟进订单和快捷操作；空状态用一句实话和一个有效动作，不用大面积诗意等待占据主要工作区。保留当前独立后台导航和表格/列表基础，不把 T-Check 的蓝白皮肤搬过来。

**验收：**1440×900 下无需长距离滚动就能扫描主要运营信息；手机先看到任务而不是欢迎海报；有数据、无数据、未配置三个状态分别审查。对应 owner admin“后台不是营销页，密集、可扫描、表格优先”。

### F07 — 父子同步已成立，但曲线与释放感仍不成立

**Evidence：E00、E03 的 hover 段、E04 的有效 press 段。测量事实置信度高；节奏选择为设计建议。**

不要把本轮问题误诊成“所有父子动画不同步”。主按钮约 95.5ms 时上移 0.7248px，箭头横移 1.0872px；各自目标是 2px / 3px，进度比例一致。

问题在 [motion.ts:7](C:/Users/123/Desktop/PinDou/05_studio/src/motion.ts:7) 的 480ms 与 `cubic-bezier(.22,.1,.22,1)`：前约 100ms 已走约 36%，而 T-Check 的 `300ms ease-in-out` 同时点约 23%。前面更急，后面更长，不能用“总时长更长”证明更舒缓。选中底板、切页、弹窗进入还使用另一条前段更快的 travel 曲线；必须按效果分别验收。

另外，[motion.ts:64](C:/Users/123/Desktop/PinDou/05_studio/src/motion.ts:64) 的最短按压保留将快速点击扩展为一段固定视觉按住。有效采样中，鼠标按住约 35ms 后松开，183ms 仍为 `data-pressed=true`，元素还在继续向下；约 500ms 才接近复位。这不是请求被延迟，而是视觉状态滞后于手指。

**改法：**先拿 T-Check 的 `300ms ease-in-out` 做真实对照版本。若仍需放慢，保留缓动形状后小幅调整，并通过按下/松开中间帧和真人操作选定；不要全站一起拉长。按钮、图标、阴影继续共用控制曲线。把较长节奏留给照片/叙事和面板过渡，避免每次筛选都让整个工作区做一遍大位移。评估取消全局固定 180ms 保留，或者将短按可见性处理限于不会与逻辑状态冲突的反馈，不延迟真实操作。

**验收：**分别记录 hover、长按、35–60ms 短按、快速二连点、键盘 Space、触屏取消；父子比例仍同步，松开后开始回程，不出现“操作已完成，旧按钮还继续下沉”。T-Check 是控制质量参照，不是要求 PinDou 所有照片和章节动画都限定 300ms。

### F08 — 拼豆组装的关键过程被父级透明度藏住

**Evidence：E00、E04。状态：逐帧复现；置信度高。**

`BeadMark` 的每颗豆子在挂载时就开始 CSS 动画；父级 `.hero-footnote` 却在另一条 GSAP 入场链中延后显现。实际采样 250ms 时父级 opacity 仍为 0，首颗豆子已完成约 96% 的位移；约 650ms 时父级才到 0.81，最后一颗豆子也已接近终点。用户主要看到的是完成形态逐渐显现，而不是一颗颗组装。

位置：[BeadMark.vue:37](C:/Users/123/Desktop/PinDou/05_studio/src/components/BeadMark.vue:37) 的独立 delay、[motion.css:119](C:/Users/123/Desktop/PinDou/05_studio/src/styles/motion.css:119) 的 CSS animation、[Home.vue:52](C:/Users/123/Desktop/PinDou/05_studio/src/pages/Home.vue:52) 的父级入场。

**改法：**先确定它是主叙事还是辅助标记。若作为本网站有辨识度的主要运动，应进入同一时间轴，在父级已经可见后开始组装；首页其余文字/照片动效保持安静。若只是脚注图案，则不值得让首屏所有元素等待它。花形标志、拼豆图案、圆形贴章也要有主次，避免每个装饰都争当品牌焦点。

**验收：**冷启动、热缓存、字体慢加载、中文/英文都能看见预期的组装过程；关闭动效时直接呈现完整图案。不能只用“代码存在 animation”证明用户看见了动画。

### F09 — 触控目标不能只看图标视觉大小

**Evidence：E00、E01、E05。尺寸已测量；按项目触控基准评审。**

390px 后台语言切换实测约 14.4×30px；商品编辑“上架出售”开关为 44×26px，旁边说明不是可点击 label；“清除筛选”高度约 26px。公共站语言/购物车/菜单也有 35–37px 的宽度。它们可能没有布局溢出，但触摸选择仍偏苛刻。这里使用项目 44px 触控目标，不冒充对 WCAG 合规性的完整审计。

位置：[desk.css:208](C:/Users/123/Desktop/PinDou/05_studio/src/styles/desk.css:208)、[motion.css:196](C:/Users/123/Desktop/PinDou/05_studio/src/styles/motion.css:196)、[ToggleSwitch.vue:6](C:/Users/123/Desktop/PinDou/05_studio/src/components/ToggleSwitch.vue:6) 以及公共头部移动端宽度覆盖。

**改法：**让点击外壳达到至少 44×44，开关可继续保持 26px 的视觉轨道；语言和图标按钮设置明确最小宽高。320px 先重新分配品牌与动作栏的网格/间距，不用压小点击区解决。商品编辑中中文名/英文名可各占整行，价格/库存保留双列。

**验收：**测量真正接收点击的元素，检查相邻目标不重叠；鼠标、触摸、键盘三种方式都能操作。现有抽屉关闭按钮和菜单主按钮 44×44，保留它们。

### F10 — 复制和加载失败仍缺少实际下一步

**Evidence：E00、E04。复制失败已受控复现；小店缺重试为源码确认。**

模拟剪贴板权限拒绝后，点击微信号只恢复原文，没有错误提示或替代动作。位置：[Home.vue:101](C:/Users/123/Desktop/PinDou/05_studio/src/pages/Home.vue:101)。这不代表所有微信浏览器都会拒绝剪贴板，而是拒绝发生时当前没有恢复路径。

小店 [Shop.vue:36](C:/Users/123/Desktop/PinDou/05_studio/src/pages/Shop.vue:36)、`:77` 只显示目录错误文字，没有重试按钮，与预约页并不一致。

**改法：**复制失败给一句明确提示，并提供可选中/长按复制的微信号；错误通过现有 Toast/状态区反馈。小店重试需要真正重新载入目录。成功消息也检查上下文：用户已经到购物车后，不再提示一个指向当前页的“去看看”。

**验收：**拒绝剪贴板、目录请求失败、失败后重试各有可执行下一步；不要只显示“出了点问题”，也不要承诺未实现的自动通知。

### F11 — 照片舞台稳定，但连续翻页会堆叠旧图

**Evidence：E00、E03、E05。连续翻页行为已复现；视觉取舍为设计建议。**

约 50ms 间隔连续点五次“下一张”，`.photo-stage figure` 最多同时存在 6 个，最终回到 1 个。没有发现永久节点泄漏，但中途可见多张照片和说明的叠影。截图：[快速翻页的中间状态](C:/Users/123/Desktop/PinDou/artifacts/studio-0830-review/press-home-rapid-gallery.png)。

位置：[PhotoViewer.vue:18](C:/Users/123/Desktop/PinDou/05_studio/src/components/PhotoViewer.vue:18)、`:48` 和 [motion.css:280](C:/Users/123/Desktop/PinDou/05_studio/src/styles/motion.css:280)。

**改法：**保留稳定图片舞台和当前 focus/scroll 管理，但中断旧过渡并直接朝最新目标前进，最多保留当前图与目标图；不要让旧图不断排队离场。图片与说明分层，避免多份文字同时浮动。手机照片框可减少过大的上下空白，但低高度下仍需完整图片、可见关闭键和稳定尺寸。横向轻扫属于后续增强，显式前后按钮仍必须保留。

**验收：**快速连点、方向反转、加载慢图片时均不空白、不堆多重残影；最终索引、图片、说明一致。已有 Escape、关闭后焦点返回和滚动恢复已通过，不能在返工时回退。

### F12 — 样式治理必须和视觉返工一起做

**Evidence：E00、E02、E06。由 F02/F04 的静态与动态交叉证据确认。**

[main.ts:6](C:/Users/123/Desktop/PinDou/05_studio/src/main.ts:6) 顺次引入基础、typography、interactions、layout、commerce、motion、viewport；后台再加载 desk。分文件本身没有错，问题是同一组件的颜色、字形、尺寸、定位与状态在不同文件反复覆盖，旧选择器仍留在关键路径中。当前徽标拉伸、商品字号和中文字体回退就是实际结果。

**改法：**以组件拥有者收拢商品卡、按钮、表单、抽屉和后台标题规则。基础层只保留 reset/tokens；响应式层主要负责排布与尺寸；动效层负责状态过渡，不再顺手重设文字与装饰风格。删除确定不再使用的旧选择器，对每次更改检查同名规则和最终 computed style。不要借本次返工重写旧图纸生成器或无关系统。

**验收：**每个受影响组件有可追溯的基准和状态表；改变一个参数不会被后面的文件静默覆盖。构建和无溢出检查之外，必须新增 F02/F04 对应的实际尺寸、字体和截图复核。

## 建议采用的整体方向

不是换一套“高级模板”，而是让三种页面各做自己的工作：

| 表面 | 视觉职责 | 保留 | 缩减 / 调整 |
|---|---|---|---|
| 公共首页、日记 | 让人看见真实空间并愿意来 | 店主实拍、纸色/橄榄色、认可的英文字体 | 减少重复诗句与装饰竞争；一处有意义的拼豆运动 |
| 预约、小店、购物车 | 清楚选择、核对、完成 | 明确价格单位、服务器报价、真实可用性 | 宣传前奏缩短；商品/表单字号稳定；异常路径可恢复 |
| 店主后台 | 扫描当天任务、处理例外 | 独立导航、可保留草稿的面板、列表与详情抽屉 | 欢迎海报收敛；订单/到店/异常优先；关键说明不缩成 9px |

不建议增加新的前端框架或动画库。现有 Vue、GSAP、SegmentedControl、ToggleSwitch、SlideOver 和 StudioToast 可以继续使用，重点是职责、状态和最终呈现。

## 已验证有效、必须保留的部分

- 主按钮与箭头 hover 中间帧按比例同步；不是“子图标先跑完”的老问题。
- 照片弹窗与商品抽屉能用 Escape 关闭，焦点回到触发控件，body 从 fixed 恢复，未发现该路径的背景滚动锁残留。
- 手机后台菜单打开时背景 inert，焦点进入导航，关闭/切页恢复工作区。
- 商品编辑的未保存草稿在关闭、切到订单、返回商品并重新打开后仍保留；本轮只改浏览器内草稿，没有保存。
- 主按钮和图标在 reduced-motion 下均为 `transform:none`、`transition-duration:0s`，没有发现父子降动效不一致。
- 本地可用时段 → 加入购物车 → 查看服务端报价的路径可走通；这不是实际支付或履约验收。
- 公共页面已查看的 390/1440/2048px，以及 Firefox/WebKit 商品页均未发现根页面横向溢出；这不覆盖所有页面或所有尺寸。

## 实施路径与第二轮验收

**P01：正确性路径。**先按 E05 修 F01/F03，再按 E02/E06 修 F02/F04，避免带着错误状态讨论视觉细节。源码与取证必须仍能回指 `edaa3f8` 基线。

**P02：设计路径。**按 E01 重排手机预约与后台概览，再用 E03/E04 做按钮曲线对照和拼豆时间轴修正，最后补 E05 的触控与连续翻页问题。每步同时更新中英状态，不靠叠更多 CSS 收尾。

**P03：回归路径。**实施任务提交以下材料后复审：

1. 新实现 SHA、预览/线上资源身份；本轮每个 F 编号的处理或暂缓理由。
2. 320×568、390×844、768×1024、1080×665、1440×900、2048×1017：公共首页、预约、小店、购物车、后台概览/订单/编辑抽屉。桌面与手机都包括长中文名、长英文名、无数据、未开放状态。
3. F01 的一次目录失败→重试和连续失败；F03 的旧筛选→指标下钻；F02 的徽标/标题尺寸；F04 的 rendered-fonts。
4. hover、短按、长按释放、二连点、取消触摸；父子逐帧；拼豆父级可见性；照片快速连点。不要只提交最终静止截图。
5. reduced-motion、键盘焦点、Escape、背景滚动锁、草稿保留、报价刷新中的旧金额与禁用状态。
6. 真机 iOS Safari、iOS 微信、Android 微信：键盘打开/收起、旋转、后台返回、复制微信、支付跳转/返回。涉及真实支付的测试需要单独按商户测试流程执行，不以本次截图或模拟 UA 代替。

真实营业参数、税务设置、上线收款决定不属于本次视觉返工自动授权范围。本轮不对支付回调、退款、真实履约或生产安全审计作“全部通过”结论。

## 证据索引与适用限制

证据时间为产物完成时间 UTC；E00 是冻结源码。审查采用通用工程报告结构，不套用安全/攻击报告分类。

| Evidence | 来源 / 观察 | 产物或定位 |
|---|---|---|
| E00 | file：冻结应用源码；静态因果定位 | `edaa3f8` Git 树；各 F 中列出的具体文件与行号，复核命令见下 |
| E01 | screenshot + browser DOM：实际页面、尺寸、可见控件 | [browser-evidence.json](C:/Users/123/Desktop/PinDou/artifacts/studio-0830-review/browser-evidence.json)，2026-09-07T23:47:04Z；正文所链 PNG |
| E02 | browser CSS / rendered fonts | [rendered-fonts.json](C:/Users/123/Desktop/PinDou/artifacts/studio-0830-review/rendered-fonts.json)，2026-09-07T23:39:31Z |
| E03 | browser：按钮 hover 帧、照片/抽屉焦点与关闭 | [interaction-evidence.json](C:/Users/123/Desktop/PinDou/artifacts/studio-0830-review/interaction-evidence.json)，2026-09-07T23:41:39Z |
| E04 | browser：有效短按、拼豆帧、拒绝剪贴板、QA 购物车、草稿 | [round2-evidence.json](C:/Users/123/Desktop/PinDou/artifacts/studio-0830-review/round2-evidence.json)，2026-09-07T23:44:19Z |
| E05 | browser：目录故障恢复、指标筛选、触控尺寸、快速翻图、降动效 | [round3-evidence.json](C:/Users/123/Desktop/PinDou/artifacts/studio-0830-review/round3-evidence.json)，2026-09-07T23:47:06Z |
| E06 | browser：Firefox 桌面 / Windows WebKit 手机尺寸商品页 | [cross-browser.json](C:/Users/123/Desktop/PinDou/artifacts/studio-0830-review/cross-browser.json)，2026-09-07T23:47:37Z |

E03 中第一次 `press` 采样因路由切换后元素卸载而无效，**不用于按压结论**；F07 使用 E04 中保留在原页、`connected=true` 的重新采样。E03 的 hover 与弹窗记录有效。WebKit 是 Windows 上的浏览器引擎检查，手机尺寸/微信 UA 是模拟环境，不是 iPhone 或微信真机验收。

原始 JSON 的 SHA-256：

```text
browser-evidence.json      0e25f241843dea155a72499eb5d3528367112408c814862fc70a52f43e203e6d
rendered-fonts.json        5dd73322358f26c74b5e345667680437a4fd4f929ae2606ad1a2e11080f62e5a
interaction-evidence.json  9a51bf858b19d45a1a4c2c4c6256b5e05c8d6d284c14b043d2897d39b8ac2727
round2-evidence.json       8a787e72c04e8b994a3986ceb58b5b3d4a390dc4365ff0ae7667b1c9fffcd3c9
round3-evidence.json       519e235fdddec4106a59a3b68a5b5756b829479a9cf732e4f5a22042154418b5
cross-browser.json         bb739c135c6ad022e47b45ed70331f65603cef98e508d6cef2ec39e42c91b383
```

离线复核命令（不会运行服务器、修改数据或创建订单）：

```powershell
git -C 'C:\Users\123\Desktop\PinDou' show 'edaa3f8:05_studio/src/pages/Visit.vue'
Get-Content -Raw 'C:\Users\123\Desktop\PinDou\artifacts\studio-0830-review\round3-evidence.json'
Get-FileHash -Algorithm SHA256 'C:\Users\123\Desktop\PinDou\artifacts\studio-0830-review\round3-evidence.json'
```

交互脚本保留在相同证据目录：`browser-review.cjs`、`interactions.js`、`round2.js`、`round3.js`、`cross-browser.cjs`。其中 round2/round3 依赖本地 QA 和浏览器驱动上下文，不是可以对生产直接运行的单文件支付测试；复现步骤以各 F 的说明为准。不要覆盖本轮证据文件，返工后另建证据目录。

## 参照依据与文档自检

- 当前 T-Check 本地参照 HEAD：`067008cfbd869cd548c78532ad269837cb01f97e`；只读检查，没有连接或变更 Turnitin 服务。
- [index.css:8](C:/Users/123/Desktop/Turnitin_generation/admin-dashboard/css/index.css:8)：实际卡片运动契约，控制基线 `300ms ease-in-out`；[help-card:831](C:/Users/123/Desktop/Turnitin_generation/admin-dashboard/index.html:831)；[generate.html:129](C:/Users/123/Desktop/Turnitin_generation/admin-dashboard/generate.html:129)：小卡片、按钮和图标的关系。
- [FRONTEND_INTERACTION_AND_MOTION_STANDARD.md](C:/Users/123/Desktop/Turnitin_generation/docs/FRONTEND_INTERACTION_AND_MOTION_STANDARD.md)：父子同步、可读性、交互层级、状态保留、触摸与中间帧验收。采用其原则，不复制配色或全部页面布局。
- Owner playbook 的交接保留副本：[01-frontend.md](C:/Users/123/Desktop/PinDou/artifacts/studio-design-sources/01-frontend.md)、[03-admin-dashboard.md](C:/Users/123/Desktop/PinDou/artifacts/studio-design-sources/03-admin-dashboard.md)。本次读取这些已保留的 master 副本，没有将其表述成重新拉取的远端最新版本。
- PinDou 自身的 [STUDIO_V1.md](C:/Users/123/Desktop/PinDou/02_product/STUDIO_V1.md)、[STUDIO_COMMERCE_V1.md](C:/Users/123/Desktop/PinDou/02_product/STUDIO_COMMERCE_V1.md)、[STUDIO_DESIGN.md](C:/Users/123/Desktop/PinDou/03_design/STUDIO_DESIGN.md)、[STUDIO_MOTION_AND_DESK.md](C:/Users/123/Desktop/PinDou/03_design/STUDIO_MOTION_AND_DESK.md)：业务事实、实拍来源、角色区分与既有约束。既有验证报告只作背景，不当作本轮视觉验收。

- [x] 每项发现均有 Evidence 和源码位置，并区分测量事实、设计判断与未验证项。
- [x] 关键功能/渲染问题使用静态代码与动态浏览器证据交叉验证。
- [x] 给出复现、改法、分批实施路径及第二轮验收要求。
- [x] 保留有效实现；没有虚构营业、库存、支付订单或真机验收结果。
- [x] 第一轮未编辑应用源码、旧生成器或生产配置；只交付审查文档与取证产物。
