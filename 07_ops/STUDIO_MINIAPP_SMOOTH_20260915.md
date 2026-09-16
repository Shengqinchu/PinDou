# 小程序流畅度改造与验收

来源：店主要求调查成熟小程序、SaaS、GitHub 方法并实际优化；随后确认不足两小时空档规则。原始服务端测量见 [基线调查](../01_research/STUDIO_MINIAPP_PERFORMANCE_20260915.md)，空档规则的独立正式部署见 [规则验收](STUDIO_SHORT_GAPS_20260915.md)。

## 方案比较与决定

本项目证据支持先修页面生命周期、渲染通信与关键内容等待链。服务端资源和摘要耗时没有支持“先升配服务器”的结论；付费网关的网络收益也未在加拿大实际链路测量。

| 方案及一手来源 | 解决范围、限制 | 本轮选择 |
|---|---|---|
| [美团扫码付小程序优化](https://tech.meituan.com/2018/09/13/scan-to-pay-mini-program.html) | 2018 年工程案例；区分启动、交互、包与请求成本。历史成绩不能当本店成绩。 | 采用分阶段测量与只缩短关键路径的方法。 |
| [有赞大型 MPA 改造](https://tech.youzan.com/gua-yong-yu-ji-you-da-xing-mpaxiang-mu-de-wei-qian-duan-fang-an/) | 2020 年网页管理系统案例，共享容器/资源减少切页成本；不是微信原生实测。 | 参考保留工作区思路，原生表现另验。 |
| [uni-app 性能指南](https://uniapp.dcloud.net.cn/tutorial/performance.html) | 减少逻辑/渲染跨层通信和重复渲染；App-nvue/uni-app x 不能直接套用。 | 取消常驻列表滚动事件，合并设备读取，按需首次创建视图。 |
| [uni-app tabBar](https://uniapp.dcloud.net.cn/collocation/pages?id=custom-tab-bar) / [路由](https://uniapp.dcloud.io/api/router.html) | 原生 tabBar 2–5 项；现有生成器已有独立 tab 路由，顾客 3 项与后台 4 项不能简单合成一个原生 tabBar。 | 顾客、店主各一个保留工作区，兼容旧页面路径和原生详情返回；保留生成器。 |
| [uni-app virtualHost](https://uniapp.dcloud.io/tutorial/vue3-api.html) | 微信组件额外宿主节点影响 flex/百分比高度，不能由 H5 布局通过推断原生通过。 | 共享外壳、导航、品牌及顾客工作区包装使用虚拟宿主，让实际首层视图参与布局；检查编译产物，仍需手机验收。 |
| [腾讯 RUM](https://intl.cloud.tencent.com/zh/products/rum?lang=zh&pg=) / [接入说明](https://cloud.tencent.com/document/product/248/87250) | 监测性能/错误的服务，需项目、SDK 与上报域名配置；监测本身不消除页面重建。 | 作为未来真实用户监测选项，本轮未接入上报、未购买。 |
| [阿里 ARMS 微信监测](https://help.aliyun.com/zh/arms/browser-monitoring/getting-started/monitor-wechat-mini-programs) | hook App/Page 与网络/错误采样，需 SDK 和域名配置；同样不是渲染加速器。 | 暂不新增第二套监测。 |
| [腾讯云小程序加速](https://cloud.tencent.com/document/product/1811/123089) | 托管网关和 SDK 改变网络路径；需实例、域名/请求白名单配置。无法修客户端销毁/创建。 | 已核对实际加速型 SaaS；先完成客户端改造，若网络仍为瓶颈再同地区对照测试，未假定价格或购买。 |

开源参考均保留当前品牌与 Vue 架构，没有整库替换：

| GitHub 项目 | 用途 | 对当前项目的判断 |
|---|---|---|
| [wechat-miniprogram/weui-miniprogram](https://github.com/wechat-miniprogram/weui-miniprogram) | 微信官方表单/列表交互组件 | 可参考结构与触控，不会自动修复请求和生命周期；未新增依赖。 |
| [Tencent/tdesign-miniprogram](https://github.com/Tencent/tdesign-miniprogram) | 腾讯小程序组件体系 | 可用但全量换 UI 增加重验成本；目前没有必要。 |
| [SmileZXLee/uni-z-paging](https://github.com/SmileZXLee/uni-z-paging) | MIT，uni-app 分页/虚拟列表等 | 列表很长时合适；当前 20–30 条分页优先保留页面与滚动，不引入更重列表框架。 |
| [wechat-miniprogram/recycle-view](https://github.com/wechat-miniprogram/recycle-view) | 微信官方可视区回收列表 | 项尺寸和集成有限制，不是小列表切页问题的直接修复。 |

## 已实现

- 顾客首页/预约/账号，店主工作台/预约/消息/营业状况，首次进入创建，之后保留组件。详情继续原生压栈/返回，旧二维码路径可用；快速点按以最后目标为准，页栈有界。
- 一次获取窗口尺寸/安全区，工作区共用上下文。显示、隐藏、旋转、键盘事件按实际生命周期处理，不重复设置相同原生标题。
- 保留实际列表滚动容器与搜索/分页；隐藏消息页停止轮询。写后失效、短期缓存、权限/账号隔离继续保留，不把缓存有效期无限延长。
- 资料/余额完成后即显示，店主提醒绑定等非关键慢请求不再挡住账号首屏。退出登录或切换账号后迟到响应不得恢复私有内容。
- 功能页入场缩短为 160–220ms，按钮反馈 120ms；首页保留品牌展示。开启微信 `lazyCodeLoading: requiredComponents`，未做未经验证的 Skyline 或整框架迁移。
- 0.1.21 手机预览反馈：“左上角 logo 总是闪烁，在切换时候”。后续候选 **0.1.22** 把顾客顶栏与底部导航移到工作区共同外壳；logo 仅一份，切 tab 不再隐藏/显示不同图像节点。方形原图明确占位尺寸，替换加载后测高的 widthFix；原始 logo 图片字节未改。

## 验证及证据边界

证据目录 `artifacts/miniapp-smooth-20260915/`。fixture 全部拦截业务请求，不发送真实预约、短信或订阅通知。

- 35 次导航源码测试：常用 tab 无原生页面创建/销毁，覆盖详情返回、旧链接、同 tab 筛选、快速连续导航与页栈上限。
- 窗口生命周期测试：首次 setup/show 一次窗口读取，共享子视图、键盘监听释放/恢复、旋转/安全区、缺失 resize 数据及语言切换通过；基线同一模拟路径为 7 次。次数不等于真机耗时。
- 顾客与管理缓存测试通过：并发去重、强制/过期刷新、账号隔离、在途失效、写后失效和退出。
- Chromium/WebKit × 中英 × 390×844 / 844×390，共 8 组工作区流程通过。列表保持同一个滚动节点及 350px 位置；热切换不增加列表请求；隐藏消息页不轮询；详情返回和退出后的迟到响应核对通过。
- 0.1.22 修正后的上述 8 组流程还检查单一顶栏/导航及逐帧 logo：连续切换期间节点未替换、位置固定、可见。H5 固定高度页面的额外 44px 页面滚动已在工作区范围内修正；这不是手机原生渲染验收。
- 在可控 fixture 中人为把非关键店主元信息延迟 2.5 秒：基线账号内容约 2909ms 才就绪，候选约 50–155ms。只说明等待链已拆开，不代表线上所有用户的加载时间。浏览器热切页计时约 33–74ms、差异很小，不宣传倍数/FPS 提升。
- MP/H5 构建通过。旧项目全量 vue-tsc 仍有生成器类型和 `studio-profile.vue` 既有 width.value 等错误；改动文件无新增类型报错，不称全项目类型全绿。网站独立构建/类型及 80 个文案模块检查通过，文案未改。
- 微信开发者工具能接官方 CLI/预览，Tool.getInfo 返回版本，但本轮 App.getCurrentPage 桥接超时；没有拿到可信的原生运行时帧率或自动化页面结果。已转由店主手机验证，不把桌面截图作为真机结果。

核心证据：`workspace-results.json`、`brand-*.json`、`baseline-results.json`、`workspace-probe-*.json`、`build-*-logo.txt`、`typecheck-final.txt`、预览信息/冻结包清单。

## 发布状态

- 服务端空档规则已正式上线，见独立发布记录。
- 最后经公众平台刷新确认的正式小程序为 **0.1.19**，2026-09-15 21:05:30 加东；0.1.20 仅开发/体验。
- **0.1.21** 只生成官方预览；店主反馈 logo 闪烁，未当作通过、未正式发布。
- **0.1.22** 修正 logo 后已通过官方 CLI 预览及开发版上传。冻结包 `release-0.1.22` 共 267 文件、1,778,411 原始字节；逐文件 SHA256 与 `package-manifest-0.1.22.json` 核对一致。官方预览包 1,683,972 bytes、上传包 1,684,994 bytes。预览码已交店主手机复测，尚未收到修正版结果，尚未提交审核/正式发布。`preview-info-0.1.22.json`、`upload-info-0.1.22.json` 保留，不将上传当上线。
- 有限授权点击任务仍停止，本轮没有恢复；没有购买 SaaS、创建新监测账号或新增外部用户数据上报。
