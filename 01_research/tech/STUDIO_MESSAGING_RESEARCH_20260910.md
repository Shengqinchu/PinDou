# PinDou 预约通知、站内沟通与自有微信小程序调研

> 2026-09-11 后续：Server 酱已接入、Telegram 代码已上线但实际绑定暂停，自有小程序 0.1.7 已提审。店主新增要求自有小程序服务通知、顾客邮箱/短信及加拿大为主兼容 +86。本次已通过官方 API 实测可用订阅模板，具体接收权限、消息产品设计和短信通道条件见 [通知与沟通方案](STUDIO_MESSAGING_PLAN_20260911.md)。下文保留初次调研时的状态和报价快照。

建议先在现有网站里增加“按预约沟通”的轻量对话，再通过 Server酱 Turbo 把新预约和顾客留言提醒发到店主微信，同时接 Telegram 作为独立备用渠道。自有小程序另做品牌授权与预约入口，不让发布审核影响店主及时收通知。这个组合最贴合当前一间工作室、少量店主、强调简洁且已经有独立预约后台的产品。

如果以后需要多人客服、咨询分配、跨渠道收件箱和现成客服手机 App，优先重新评估 Chatwoot。当前直接引入整套客服平台，会增加第二个后台、身份同步和维护工作。本文对“原站扩展优先”的判断是针对本项目的工程取舍，并不代表 Chatwoot 的通用能力不足。

本轮调查截至 2026-09-10 Toronto，GitHub 元数据最后采集于 13:11 UTC。核查了 22 个仓库、主要候选的发布记录与许可、官方产品文档，并检查了本地业务代码，实际编译了已有小程序。平台额度与价格是调查时快照；未创建外部服务账号、未订阅付费服务、未发送真实通知，也未上传或发布小程序。本报告中的新功能均为待实施方案。

## 1. 现在的缺口与最先要解决的问题

店主需要在顾客“提交预约、等待确认”时就收到提醒。不能只订阅“预约已确认”，否则提醒会出现在店主处理之后。成熟预约产品也区分这些事件：Cal.com 把需要店主确认的提交单独定义为 Booking Requested，同时有创建、取消和改期等事件。[Cal.com 官方说明](https://cal.com/help/webhooks)

本地现状依据：

| 部分 | 当前实现 | 对使用体验的影响 |
|---|---|---|
| 预约后台 | 已有预约列表、日历、状态和详情 | 可以继续作为统一处理入口 |
| 浏览器提醒 | ReservationNotifications.vue 每 20 秒请求一次；首次设置游标，之后的新单才提醒 | 页面关闭后不再检查；重新打开能看到待确认数量，但不能补成手机离线推送 |
| 服务端通知接口 | reservation-notifications 返回新增数量、待确认数和游标 | 没有消息投递记录、后台发送队列或手机渠道 |
| 顾客资料 | 已有按稳定账号保存的预约称呼与联系方式 | 可直接用于预约对话的身份展示，避免再次填表 |
| 站内聊天 | 没有预约消息表或双方回复界面 | 现有“店主私密备注”不能直接充当聊天记录 |
| 原生小程序 | 已有 uni-app 工程，本地能编译 | 尚不是可直接发布的自有扫码授权产品 |

代码位置：[浏览器提醒](../../05_studio/src/components/admin/ReservationNotifications.vue)、[预约接口](../../06_studio/reservations.py)、[预约资料](../../06_studio/booking_profile.py)。本轮检查基于提交 2227adc 及当前工作区；旧生成器目录中其他未提交工作保持原样。

优先级应是：**新预约及时提醒 → 双方围绕预约沟通 → 店主在手机端方便处理 → 自有小程序品牌与更多微信能力**。前两项可以完全复用当前 Vue + FastAPI + SQLite，不依赖先取得小程序审核结果。

## 2. 小程序能不能做：可以开发，但目前还不能直接上线

### 截图已经确认的状态

店主提供的最新后台截图显示：

- 小程序名为“双吉拼豆图纸定制”。
- 基础资料已完成，已设置一个类目，已添加一位开发者。
- 小程序备案已完成，微信认证尚未完成。
- 没有线上版本、审核版本，也没有上传过开发版本。
- 截图本身明确说明，未完成微信认证不影响后续版本发布。

因此“备案已完成”和“已经发布”是两回事。当前可进入开发、上传体验版与准备提审的流程，但没有证据可以把它描述成一个已经运行的自有授权小程序。店主回复主体类型不确定；个人、个体工商户、企业等资格以及具体接口权限继续记为待核验。

### 本地实际核查和编译结果

已有工程在 [05_frontend](../../05_frontend)。其 manifest 使用 AppID **wx9f2b4d171e92a5ef**；根目录 project.config.json 仍留着另一个以 **95ec** 结尾的旧 AppID。实际编译生成的 project.config.json 使用的是 manifest 中的当前 AppID。后续应统一开发工具配置，避免导入错误项目，而不是认定这次构建已经用了错误账号。

本轮使用现有依赖执行 build:mp-weixin，输出到独立的 artifacts/miniapp-feasibility/build，**退出码 0，构建成功**。Node 为 24.19.0；构建出现 Sass legacy API 弃用提示，没有构建失败。没有在微信真机运行，没有调用微信身份接口，没有上传到微信后台。构建成功只证明代码能够产出小程序文件。

还发现两项需要先补齐：

1. 当前页面清单中没有“扫描网站登录请求 → 查看请求 → 确认登录 → 成功返回”的完整页面流程；现有页面主要服务于旧版图纸生成器。
2. 本地 06_backend/pindou/api/user.py 的 /login 仍是早期开发占位实现：直接把传入 code 哈希成 openid，并未完成微信服务端身份交换。它不能作为自有小程序正式登录依据。这一发现来自旧小程序对应的本地代码，不能据此推断当前已上线的 Studio Authing 登录也是这个实现。

具体证据与复现见 [小程序可行性验证记录](../../07_ops/STUDIO_MINIAPP_FEASIBILITY_20260910.md)。

### 两条接入路线

| 路线 | 适合情况 | 需要完成 | 主要未决项 |
|---|---|---|---|
| 继续使用 Authing，部署自己的“小登录” | 希望沿用当前 Authing 身份桥接 | 获取对应源码与授权、改品牌、部署自有小程序、配置身份源、测试旧账号绑定 | 当前套餐是否包含、源码获取方式及费用、现有 subject 如何延续 |
| 自有原生授权页 + 我们的服务端扫码会话 | 希望完整控制品牌和流程 | 真实微信登录校验、短期扫码挑战、原手机确认、原浏览器领取会话、身份映射与绑定 | 开发与账号迁移工作更多，仍需小程序提审与实际权限核验 |

Authing 当前官方文档明确提供“私有化小程序”选项，并说明自定义页面需要联系其获取小登录源码，再部署自己的小程序、填写 AppID/AppSecret。这证明存在受支持的品牌定制路径，但不能证明当前免费套餐已包含源码或部署权益。[Authing 微信 PC 小程序扫码](https://docs.authing.cn/v2/guides/connections/social/wechat-miniprogram-qrconnect/)

建议先核实 Authing 私有小程序的实际可用条件。若条件合适，优先沿用；若不合适，再做独立扫码会话。两条路线都必须保留网站内部的同一个账号 ID。不同小程序的 openid、不同身份源的 subject 不能直接视作同一个人；无法取得可验证的关联时，通过已登录账号主动绑定，不能按昵称或联系邮箱猜测合并。

自有页面建议采用原有小狗图案、白底与浅蓝按钮，显示“正在登录 pindoupuppy.com”、明确的确认动作和结果。小程序里的站点页面可以完全自定义，但微信系统级权限弹窗、右上角胶囊等仍由微信控制。

手机自己打开网页的场景必须单独验收：电脑二维码由手机扫描，与同一手机 Safari/Chrome/微信内网页授权不是同一个流程。原生 App 拉起小程序的文档也不等于普通 H5 可以直接照搬。现阶段仍保持网站默认账号密码；微信只在用户选中时加载。

### 小程序相关能力的边界

| 想要的能力 | 当前判断 |
|---|---|
| 自己品牌的原生首页、授权说明、成功页 | 可以开发；现有代码已能编译 |
| 普通用户扫描自有小程序码登录网站 | 需要补齐真实登录、扫码会话并完成可用版本发布 |
| 把整个网站直接放进 web-view | 主体、业务域名及实际权限未核验，不能先承诺可用 |
| 顾客收到预约确认的微信订阅消息 | 可以作为后续候选；必须核验模板、用户订阅与当前类目可用范围 |
| 店主无限期、无需交互地收到全部订单提醒 | 不能因为已有小程序就认定已具备 |
| 直接用当前图纸定制类目发布预约/客服功能 | 需要核验类目覆盖和实际提审要求 |

微信官方示例将“请求订阅”和“发送订阅消息”作为独立步骤，不能把一次登录等同为永久通知许可。本轮读到了官方示例，但公开能力文档抓取失败，因此不把网上常见的个人主体、长期订阅等限制数字当作已核验的当前规则。[微信官方订阅消息示例](https://github.com/wechat-miniprogram/miniprogram-demo/blob/master/miniprogram/packageAPI/pages/api/subscribe-message/subscribe-message.js)

主体类型、类目名称和具体接口权限的核验，不妨碍我们先做网站通知及原生授权页开发；它们是发布相应功能前要补齐的信息。

## 3. 微信与其他通知渠道的比较

表中的“可回复”只指渠道具备接收上行消息的条件。把店主回复准确送回某个网站顾客，还需要我们实现账号授权、消息关联与去重。

| 渠道 | 店主在哪收 | 是否适合首次落地 | 双向沟通能力 | 关键限制 |
|---|---|---|---|---|
| **Server酱 Turbo + 微信服务号** | 个人微信 | **推荐的微信起点** | 首版使用通知中的网站入口回复 | 免费每天 5 次；会员额度更适合预约与留言 |
| **PushPlus 微信渠道** | 个人微信 | 已实名、偏好免费额度时很合适 | 有开放接口和回调，仍需自行做会话关联 | 发送方必须实名；免费实名额度 200 次/日、5 次/分钟 |
| 企业微信自建应用 | 企业微信；符合配置条件时可经微信插件接收 | 已有企业微信时优先考虑 | 可做回调与应用会话 | 需要企业/应用管理、成员身份、可信配置；当前租户未核验 |
| 企业微信群 Webhook 机器人 | 企业微信群 | 店主愿意用企业微信时很快 | 简单 Webhook 发送本身不是网站双向聊天 | 不能当作普通个人微信群机器人 |
| **Telegram Bot** | Telegram 私聊 | **推荐独立备用，后续也适合店主直接回复** | Bot API 支持接收消息、按钮与回复关联 | 店主先启动 bot；要固定接收账号；不等于顾客也要装 Telegram |
| 微信 ClawBot / Tencent iLink | 个人微信 ClawBot 会话 | 适合试验，暂不作唯一离线提醒 | 官方插件支持双向多种消息 | 依赖近期交互上下文，供应商列有主动下发次数与时间限制 |
| WxPusher | 其多端客户端、当前官网列出的微信 ClawBot | 候选备用 | 平台提供上行消息和回调 | 不把旧公众号教程直接当作 2026 当前渠道保证 |
| ntfy | ntfy 手机 App、浏览器 | 想要开放、自托管时合适 | 以提醒为主，按钮可返回网站 | iOS 自托管即时提醒仍需上游 APNs/FCM 转发 |
| Bark | iPhone 通知 | 店主以 iPhone 为主时很实用 | 通知为主 | 需安装 App；不提供网站客服收件箱 |
| 浏览器 Web Push | 支持的浏览器/安装后的网页应用 | 补充渠道 | 点通知后回站内 | 必须实现真正的服务端推送；现有页面内 Notification 不是它 |

### 微信首选为什么倾向 Server酱

Server酱 Turbo 官方把个人开发者的微信通知列为默认使用场景。调查时免费版每天 5 次，会员最多 1000 次 API 请求/日，每分钟 50 次，失败请求也计数；促销价为 CNY 8/月或 CNY 39/12 个月，最终以订阅页为准。服务号卡片与消息正文展示有通道限制，不能承诺每条微信卡片都展开全部预约资料。[Server酱 通道和额度](https://sct.ftqq.com/docs/getting-started/channels/)

对店主来说，微信中只需“新预约、日期时间、人数、查看入口”。详细联系信息和历史对话留在自己后台；平台短期保存的推送内容也不作为预约凭据。Server酱的示例代码可以参考，但它的 MIT 示例仓库不意味着托管通知服务本身可以完整自建。

如果不想订阅，PushPlus 是值得优先试的替代。其实名用户的微信渠道有 200 次日请求额度，同时有每分钟 5 次、相同内容每小时 3 次的限制。我们应做合并提醒和错误退避，不能靠无限重试消耗额度。[PushPlus 系统额度](https://pushplus.plus/doc/guide/use.html)

PushPlus 的实名不是仅填一个昵称：官方要求姓名、证件、手机号等验证，并说明每次认证调用收费；没有中国居民身份证的海外用户需要按其说明人工处理。不能把“免费发送额度”写成“完全没有接入门槛或任何费用”。[PushPlus 实名说明](https://pushplus.plus/doc/function/verify.html)

PushPlus 的微信客服消息激活窗口也会影响卡片展示方式。其说明中，主动激活后有 48 小时客服消息窗口，每次交互最多 5 条，之后回落到模板消息。因此我们测试的应是店主实际锁屏后的提醒效果，而不只是电脑端 API 返回成功。[PushPlus 激活说明](https://www.pushplus.plus/doc/help/activation.html)

### 企业微信：可以考虑，但要分清产品

腾讯自己的 HiFlow 文档支持通过企业微信群机器人 Webhook 投递消息，并要求已有企业微信、加入企业与群管理权限。它支持的是企业微信群场景，不是为任意个人微信群提供同样的开放 Webhook。[腾讯 HiFlow 企业微信群机器人](https://hiflow.tencent.com/docs/applications/wwx-robot/)

WeComChan 作者给出了“自建应用 → 微信插件 → 个人微信”的实现，可参考其消息发送代码。但仓库最近推送为 2024 年，README 中“无需认证即可使用”等资格描述不能直接替代 2026 年实际租户验证。本轮企业微信原始帮助页和 API 页抓取失败，所以这条路线保留为条件候选，不宣称店主现在已经满足资格。[WeComChan 源码与接入说明](https://github.com/easychen/wecomchan)

如果店主已经使用企业微信，它可替代第三方微信推送服务；若尚未使用，为一间小店首次接入新预约提醒而引入企业注册、应用管理和成员设置，工作量会更大。

### Telegram：最容易把“提醒”继续做成“回复”

店主在自己的 Telegram 中先与 bot 开始一次对话，服务端以后使用 Bot API 发摘要和链接。顾客依旧留在 pindoupuppy 网站，不需要 Telegram。官方平台支持 HTTPS API；普通低频消息不需要开启付费广播。[Telegram Bots](https://core.telegram.org/bots)、[Bot FAQ](https://core.telegram.org/bots/faq)

后续可把 Telegram 消息 ID 与网站预约/消息 ID 关联：店主回复某条 bot 消息，我们验证发送人后，将回复写入对应站内对话。接收消息可选 Webhook 或 long polling，不能同时启用；Webhook 使用官方 secret_token 验证请求，并按 update_id 去重。[Telegram Bot API](https://core.telegram.org/bots/api)

第一版建议只有“查看预约”“查看留言”按钮，预约确认继续进入原后台。若以后增加 bot 内确认，必须再次检查预约版本和容量，防止用一条旧通知确认已经变更的时段。普通自由文本回复不自动触发改期、扣积分或确认预约。

### 2026 年的微信 ClawBot，不能遗漏，也不能夸大

腾讯已经公开官方 openclaw-weixin 插件，并提供 iLink 的收发协议；它支持扫码连接和双向文本、图片、语音等消息。因此“个人微信完全没有官方 bot 路线”已经不是适合本轮调研的结论。[腾讯官方插件](https://github.com/Tencent/openclaw-weixin)、[协议说明](https://github.com/Tencent/openclaw-weixin/blob/main/docs/protocol_zh_CN.md)

但 PushPlus 对它当前接入的说明列出：先扫码绑定并主动发消息，每下发 10 条需要再次主动对话，每隔 24 小时也需要主动对话。这些具体数字是本轮从供应商文档读到的接入规则，腾讯公开协议中没有找到对应的长期可用性保证；后续变化应重验。[PushPlus ClawBot 说明](https://pushplus.plus/doc/channel/clawbot.html)

同时，官方仓库有尚未关闭的用户反馈：接口返回 ret=0，但微信端未出现消息。该问题从 8 月 27 日提交，9 月 8 日仍有更新；这是用户报告，并非我们独立复现或证明服务普遍故障。[腾讯仓库 issue 268](https://github.com/Tencent/openclaw-weixin/issues/268)

店主通知最关键的情景是“几天没打开后台，突然有人预约”。需要定期互动才能维持的通道不适合作为唯一保障。可以以后把 ClawBot 用作互动查询或辅助回复，核心新单通知保留其他渠道。单纯发送一条预约摘要也不需要部署一整套 LLM/OpenClaw。

### WxPusher、ntfy 与 Bark 的位置

WxPusher 当前官方网页列出多端客户端、ClawBot、发送状态和上行消息。其标准 API 是异步分发，响应成功表示任务已创建。旧 GitHub 索引很久未更新，但新移动客户端有 2026 年更新，不能因此断定整个平台停更；也不能继续无条件引用旧公众号接入教程。[WxPusher 当前入口](https://wxpusher.zjiecode.com/)、[标准 API](https://wxpusher.zjiecode.com/docs/api-reference.html)

还要区分服务接入与代码再利用：新的移动和桌面客户端采用自定义协议，对商业使用、修改后分发有明确限制。它们不是可以直接换上小狗 Logo 再公开发布的宽松许可客户端。调用托管服务则应单独看服务条款。[移动端许可](https://github.com/wxpusher/wxpusher-app/blob/master/LICENSE)、[桌面端许可](https://github.com/wxpusher/wxpusher-desktop/blob/master/LICENSE)

ntfy 可以自建并通过 HTTP 发布提醒，但官网文档特别说明：iOS 及时收到自托管通知仍需上游转发到 APNs/FCM，否则可能明显延迟。对本项目而言，它是开放的备用推送方案，不是完全不依赖移动平台基础设施的“绝对即时”通道。[ntfy iOS 配置](https://docs.ntfy.sh/config/#ios-instant-notifications)

Bark 利用 APNs，适合店主 iPhone 的提醒、分组和点击返回网站。它没有现成的预约会话后台；如选用，只替换通知出口。[Bark](https://github.com/Finb/Bark)

## 4. 站内沟通如何融入现有页面

建议每条预约保留一个对话，称呼和联系方式从刚完成的个人资料功能读取；历史预约继续保留当时资料快照。用户改了个人资料，不会把旧记录内容全部重写。

顾客在“我的预约”或预约详情点“联系店主”。展开后首先看到简短的预约摘要，然后是消息和输入栏；不再弹出另一套名称、邮箱、电话的注册表单。未读消息用一个数量标记提示，没有新消息时不占一整行解释文字。手机端在现有抽屉/页面里打开，键盘弹起时保留输入框可见。

店主后台给预约增加“有新消息”筛选和最后一条消息摘要；打开详情即可回复。对外回复和店主私密备注在数据与界面上明确分开，已有私密备注绝不能直接回传给顾客。预约仍有 pending/confirmed/completed/cancelled 等业务状态；对话是否已读或已处理另行记录，不能用“关闭聊天”代表“取消预约”。

这种设计采用客服 SaaS 的身份验证、会话历史与未读管理思想，同时保留我们自己的预约页面。Chatwoot 官方也区分可见联系信息与经过验证的身份：网站集成应以稳定 ID 和服务端生成的 HMAC 来确认联系人，不能相信浏览器自己填写的邮箱就给予历史消息访问权。[Chatwoot 身份说明](https://www.chatwoot.com/hc/user-guide/articles/1782283175-understanding-contact-identity-and-identity-validation-in-chatwoot)

网站当前新预约提交已要求登录，因此首版站内会话直接绑定该预约 owner_id；不必新增匿名聊天系统。遗留无 owner_id 的旧预约不按姓名自动认领，待原有访问凭据和明确绑定流程核验后再开放对应会话。

顾客离线时，回复仍保存在账号内；再次进入网站可继续查看。**首版只给店主配置微信/TG，不代表顾客关掉网站后也一定收到外部提醒。** 顾客离线提醒是单独的一项：以后在个人设置选择订阅微信消息或浏览器推送，验证有效后启用。用户没有选择外部渠道时，不会把“站内已保存”显示成“已送达微信”。

遵守项目设计 skill：保持 Vue、原有品牌、双语内容模块、16px 输入字号与手机可视视口适配；入口按需展开。新增状态和系统消息只服务预约沟通，不增加全站自动弹出的客服问候或不必要的大字说明。需要真正滚动的聊天记录自然滚动，避免为了“一屏”裁掉输入框和焦点边框。

## 5. 开源候选与部署取舍

所有星标和最后推送时间可在 [GitHub 调查快照](studio_messaging_github_20260910.json) 复核。它们用于发现活跃项目，不能替代许可检查、故障测试或移动端真实送达验证。

| 候选 | 对本项目的价值 | 建议 |
|---|---|---|
| **Apprise** | Python 统一通知适配，支持 Telegram、Server酱、PushPlus、WeCom、ntfy、Bark 等 | 多渠道扩展优先；两条简单出口也可以先直接调用官方 HTTP API |
| **aiogram** | Python 异步 Telegram bot；方便接回复、按钮和回调 | 第二阶段做店主手机回复时优先 |
| python-telegram-bot | 另一成熟 Python Telegram 框架 | 可替代 aiogram，不同时引入两个框架 |
| **Chatwoot** | 完整客服收件箱、私密备注、多客服与现成手机 App | 完整客服场景的首选；当前保留为扩展方案 |
| Novu | 通知模板、偏好、渠道编排与站内通知中心 | 对现阶段规模偏大，也不直接等同双方聊天 |
| ntfy / Bark | 手机提醒出口 | 微信/TG 之外的备用选择 |
| Gotify | 自托管提醒，官方 Android 客户端 | 店主目前展示 iPhone，优先级较低 |
| WeComChan | 多语言企业微信应用发消息样例 | 参考实现；权限与可信配置按当前官方后台验证 |
| Wechaty | 基于不同 puppet 的聊天自动化框架 | 不作为无人值守预约通知的首选，不为本需求引入个人号自动化运行环境 |
| PushDeer | 曾有轻应用/多端推送 | README 已明确不再维护，本次排除 |
| Papercups | 可嵌入开源网站聊天 | README 明确维护模式，不作为新核心系统 |
| 微信官方 miniprogram-demo、wechatpy、WxJava | 官方交互范例或微信 API SDK | 自有小程序开发参考；SDK 不能替代真实身份校验 |

### Apprise：适配度最高，但它只是通知适配层

Apprise 与我们 Python 后端匹配，不必另外部署它的 Web 管理服务。接收渠道可以配置在服务端，业务只提交结构化事件。它的发送重试能力不能代替数据库里持久保存的待发任务；重启后要不要重发、哪些顾客消息合并提醒，仍由本项目负责。[Apprise 仓库](https://github.com/caronc/apprise)

本轮核验的稳定版本为 1.13.1，2026-08-31 发布；发布说明明确提示 2.x 会有破坏性变化。若实际采用，先锁定验证过的版本，不使用不设上限的升级范围；涉及投递状态回查时，仍为对应供应商补单独适配。[Apprise 1.13.1 发布说明](https://github.com/caronc/apprise/releases/tag/v1.13.1)

### Chatwoot：功能很全，成本主要在系统边界

其核心按 MIT 提供，enterprise 目录另有许可。自托管增加 Ruby/Rails、PostgreSQL、Redis 与任务处理组件，不能直接接入现有 SQLite。官方自托管文档列最低 4GB RAM，生产建议更高；不同指南的 CPU/版本建议有差异，实际安装要以所选版本为准。本轮没有对生产主机做容量压测，不能声称现有主机已验证足够。[Chatwoot 许可](https://github.com/chatwoot/chatwoot/blob/develop/LICENSE)、[部署要求](https://developers.chatwoot.com/self-hosted/deployment/requirements)、[自托管总览](https://developers.chatwoot.com/self-hosted)

它已有 iOS/Android 客服 App，可连自托管实例并接推送；默认手机推送可能经过 Chatwoot relay，品牌自建 App 则要处理自己的 FCM 等配置。若店主接受用 Chatwoot App 回复，这能省去自建客服手机 App 的工作。[Chatwoot 手机 App](https://www.chatwoot.com/mobile-apps)、[手机推送配置](https://developers.chatwoot.com/self-hosted/custom-mobile-app)

调查时 Cloud 免费 Hacker 方案最多 2 个坐席、500 次会话/月、30 天数据保留，只含网站聊天。Startups 页面标价 $19/坐席/月、按年付，Business 为 $39；页面抓取没有明确币种，不将这些金额写成 CAD。免费方案不宜当作长期预约历史库；付费能力和自托管能力也不要混用。[Chatwoot 价格与功能表](https://www.chatwoot.com/pricing)

Chatwoot 的 Telegram inbox 是接入从 Telegram 来的客户对话，不自动等于“所有网站留言发到店主私人 Telegram，让店主回复”。后者仍是我们自己的通知与回复桥接。若以后采用 Chatwoot，还应保持预约状态在 Studio 内权威，并通过受验证的 API/HMAC 连接账号。[Chatwoot API 分层](https://developers.chatwoot.com/api-reference/introduction)、[Telegram 渠道](https://developers.chatwoot.com/contributing-guide/telegram-channel-setup)

### Novu 与未选项目

Novu 的自托管包含 API、worker、WebSocket 服务及 MongoDB、Redis 等；官方 Vue 指南当前要求用 JavaScript SDK，明确没有原生 Vue Inbox 组件。它解决的是通知基础设施，仍需另做预约双方消息模型。对目前一间工作室，这些新增服务的收益有限。[Novu 自托管](https://docs.novu.co/community/self-hosting-novu/overview)、[Vue 接入](https://docs.novu.co/platform/quickstart/vue)

PushDeer 的 README 已明确写出停止维护，官方 Android 通道也受影响；Papercups 声明 Maintenance Mode，停止主要新功能开发。两者保留为历史参考，不承担本项目新建的核心提醒/沟通功能。[PushDeer](https://github.com/easychen/pushdeer)、[Papercups](https://github.com/papercups-io/papercups)

## 6. 建议的实现结构

下面是拟实施结构。持久消息与通知任务都留在我们自己的数据库，外部平台只负责提醒或转交回复。

~~~mermaid
flowchart TD
    Customer["顾客提交预约或发送留言"] --> Transaction["同一事务：保存业务记录和待发任务"]
    Transaction --> Website["账号与预约详情：历史、未读、站内回复"]
    Transaction --> Worker["后台投递：去重、重试、记录结果"]
    Worker --> WeChat["微信：Server酱 / PushPlus"]
    Worker --> Telegram["Telegram：摘要和查看入口"]
    WeChat --> Desk["店主手机打开原后台"]
    Telegram --> Desk
    Desk --> Website
    Telegram -. "后续：验证店主身份并关联回复" .-> Website
    Website --> Customer
~~~

把业务记录和待发通知一起写入，再由后台处理，是 transactional outbox 的基本思路。它解决“预约已保存，发消息时却失败”造成的遗漏；消费者仍须处理重复和顺序，不能因为用了 outbox 就承诺外部消息绝不重复。[AWS Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)

本项目的具体设计建议如下：

| 数据/组件 | 拟承担的职责 |
|---|---|
| reservation_conversations | 每预约一个会话，绑定稳定账号；与预约业务状态分离 |
| reservation_messages | 文本、发送角色、序号、客户端请求 ID、创建时间；首版按顺序追加 |
| conversation_reads | 双方最后已读序号；不在打开列表时把未展示内容标为已读 |
| notification_outbox | 事件、收件人、渠道、下次重试时间、处理租约、状态、供应商消息 ID |
| notification_attempts | 单次结果、错误类别与时间；记录可排查信息而不记录密钥 |
| channel_bindings | 店主接收渠道；凭据只在服务端保管 |
| telegram_message_links | Telegram chat/message 与站内预约/消息的映射，供后续回复桥接使用 |

初期用 SQLite 持久任务和一个后台发送 worker 即可，不为两条通知通道先增加 Redis 集群。执行网络请求时先释放数据库事务；多个实例或重启时由租约和条件更新控制任务领取。先投递旧消息，再投递同会话的新消息，避免答复顺序颠倒。上述是拟实现细节，不是当前已经具备的能力。

消息事件应区分：

| 事件 | 首要接收人 | 展示效果 |
|---|---|---|
| 新预约提交、待确认 | 店主 | “新预约待确认”及日期、时间、人数 |
| 顾客发新消息 | 店主 | 对应预约及未读摘要 |
| 店主确认/取消/改期 | 顾客站内 | 业务状态及系统记录 |
| 店主回复 | 顾客站内 | 新回复、未读状态 |
| 某外部渠道连续失败 | 店主其他有效渠道/后台 | 明确提示该通道异常，不把失败当成功 |

每次投递用事件 ID、收件人、渠道唯一约束去重。429 遵守供应商限流和重试等待，5xx/断网有限退避；凭据失效、取消关注等终止错误及时标记需处理。网络响应丢失时可能无法知道外部是否已收件，应保留“结果不确定”，避免无上限重试。

供应商受理、供应商报告送达、店主已读是三个不同状态。Telegram 等通道不提供我们需要的逐条已读回执时，就只写“已发送”，不能显示“店主已看到”。判断需要补提醒时，以店主在后台打开/处理的状态为准，而不是只看接口 200。

通知中默认仅包含预约编号、日期、时间、人数和登录后可打开的入口；完整联系方式、账号邮箱、私密备注和整段聊天记录不复制到第三方。链接需要后台重新鉴权，不放能直接登录或直接改预约的长期密钥。所有时间按 America/Toronto 显示并正确处理夏令时。

## 7. 分阶段交付与验收

工时是基于当前代码结构的工程估计，供安排先后，不是已承诺的交付时间；不包含供应商开户、平台审核、真机配合和等待反馈。

| 阶段 | 可审阅成果 | 估计开发与本地验证 | 外部条件 |
|---|---|---|---|
| A. 新预约主动提醒 | outbox、微信/TG 适配、后台投递状态、通知直达预约 | 1–2 个工作日 | 店主选择并绑定接收账号；如选付费服务，另行订阅 |
| B. 站内预约对话 | 顾客/店主会话、未读、原有资料带入、手机键盘适配 | 2–4 个工作日 | 无需等小程序发布 |
| C. Telegram 直接回复 | 回复映射、身份白名单、去重和回显 | 1–2 个工作日 | 店主愿意在 TG 内回复，已启动 bot |
| D. 自有小程序授权 | 品牌页面、真实身份校验、原账号绑定、体验版 | 取决于 Authing 源码路线或自研范围 | 主体/类目权限、开发者访问、合法域名、审核与真机验证 |
| E. 顾客离线微信提醒 | 用户可选订阅、确认/回复事件触达 | 模板与权限确认后再估 | 对应小程序/公众号能力及顾客明确选择 |

第 A 阶段建议微信和 Telegram 都发送新预约摘要。这样不依赖微信服务错误回执才能启动备用；后续根据店主使用习惯减少重复提醒。顾客连续留言可在短窗口内合并为一条“有新消息”，新预约本身不等批次。更复杂的定时催办只在店主明确要求后增加。

第 B 阶段先提供文字对话、未读和失败重试；图片/附件等需求有明确用途后再加。顾客第一次提交预约所保存的称呼与联系方式直接复用，不恢复已经删除的“老客可忽略”提示。

上线前需要执行并记录的验收：

| 场景 | 通过条件 |
|---|---|
| 所有后台标签页关闭后创建测试预约 | 店主手机仍收到提醒 |
| 已登录老客提交预约并留言 | 使用同一账号和已有预约资料，不再要求重复填写 |
| 重复点击提交、请求重放、worker 重启 | 预约/站内消息只记录一次；通知重复受控且可追溯 |
| 供应商断网、429、失效凭据 | 预约照常保存；任务重试或失败可见；备用通道独立工作 |
| 微信锁屏、退出微信界面、间隔两天后再通知 | 在实际店主手机核验可用性与延迟 |
| 顾客 A 尝试读取 B 的会话 | 每个接口都拒绝，不能只靠前端隐藏 |
| 店主私密备注与对外回复 | 顾客接口只返回对外消息 |
| 手机键盘、320px 宽度、大屏和中英切换 | 输入、发送按钮与焦点框完整可见；草稿保留 |
| TG 非绑定用户、重复 webhook、伪造回调 | 拒绝/去重；不能向网站会话写入 |
| Telegram 回复旧通知 | 回复到正确预约；不自动改变预约状态 |
| 自有小程序登录旧账号 | 原积分、时长、图纸和预约仍属于同一内部账号 |
| 自有扫码过期、重复确认、错误浏览器领取 | 不产生新登录会话；正常重试有清楚提示 |
| 顾客关闭网页后店主回复 | 站内保留，未配置外部渠道时不声称顾客已收到推送 |

最终真实通道验收需要一次可辨识的店主测试通知与手机确认。本轮没有执行这些发送，不把 GitHub 调研和本地编译写成已经证明通知可靠。

## 8. 仍需核验的信息与决策依据

当前真正影响下一步的外部信息只有几个：小程序主体及具体类目；Authing 私有小程序源码/权益；店主是否已使用企业微信；希望选 Server酱 的订阅额度还是 PushPlus 的实名免费额度；Telegram 接收账号。无需因此暂停网站会话和 outbox 的设计工作，也不需要在聊天中公开粘贴任何 bot token 或 AppSecret。

本轮没有取得的证据包括：微信后台实时接口权限页、微信审核结果、实际供应商账号套餐状态、店主手机真实送达记录。WeChat 原始公开文档部分抓取失败；搜索结果中出现的腾讯 Superapp/SAS 文档属于另一产品，未用于推导微信小程序资格。论坛教程、开源 issue 与项目 README 的平台资格描述，均未替代实际租户权限证明。

范围覆盖了：自有/共享小程序、个人微信服务号推送、企业微信应用与群机器人、2026 ClawBot、Telegram、开放手机推送、完整客服平台、通知编排层与相关 SDK。没有找到一个可以无需任何配置，同时完整替代网站账号、预约后台、微信授权和客服沟通的单一开源项目；更合适的做法是保留自己的业务记录，复用成熟的渠道与协议实现。

## 附录：22 个 GitHub 仓库筛选

以下星标数为 2026-09-10 的快照；“最近推送”是 GitHub pushed_at 的 UTC 日期，不等于最近正式版本、作者人工维护或已通过本项目验证。自动识别不到协议时读取了关键许可文件，未核清的标明保留。

| 仓库 | Stars | 最近推送 | 协议/状态与用途 |
|---|---:|---|---|
| [chatwoot/chatwoot](https://github.com/chatwoot/chatwoot) | 36,660 | 2026-09-10 | Ruby；核心 MIT，enterprise 独立许可；完整客服候选 |
| [caronc/apprise](https://github.com/caronc/apprise) | 17,286 | 2026-09-10 | Python；BSD-2-Clause；通知适配优先 |
| [binwiederhier/ntfy](https://github.com/binwiederhier/ntfy) | 34,132 | 2026-09-10 | Go；Apache-2.0；开放推送候选 |
| [Finb/Bark](https://github.com/Finb/Bark) | 9,054 | 2026-09-04 | Swift；MIT；iPhone 提醒 |
| [Finb/bark-server](https://github.com/Finb/bark-server) | 3,621 | 2026-07-07 | Go；MIT；Bark 服务端 |
| [gotify/server](https://github.com/gotify/server) | 15,867 | 2026-09-09 | Go；代码 MIT，logo CC-BY；Android 方向优先于 iPhone |
| [novuhq/novu](https://github.com/novuhq/novu) | 39,963 | 2026-09-10 | TypeScript；核心 MIT，enterprise 商业许可；当前较重 |
| [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) | 29,461 | 2026-09-06 | Python；LICENSE.dual 允许 GPLv3/LGPLv3 二选一；TG 框架备选 |
| [aiogram/aiogram](https://github.com/aiogram/aiogram) | 5,863 | 2026-08-26 | Python；MIT；TG 双向交互优先 |
| [easychen/serverchan-demo](https://github.com/easychen/serverchan-demo) | 131 | 2024-10-22 | MIT 示例；不是托管服务的完整开源后端 |
| [wxpusher/wxpusher-client](https://github.com/wxpusher/wxpusher-client) | 889 | 2022-07-26 | Apache-2.0；旧汇总索引，不能据此判断平台当前维护情况 |
| [wxpusher-sdk-python](https://github.com/wxpusher/wxpusher-sdk-python) | 289 | 2024-07-08 | Python；Apache-2.0；API 当前字段优先查官方文档 |
| [wxpusher/wxpusher-app](https://github.com/wxpusher/wxpusher-app) | 82 | 2026-09-05 | 新移动端源码；自定义限制许可，不作换牌商用客户端底座 |
| [wxpusher/wxpusher-desktop](https://github.com/wxpusher/wxpusher-desktop) | 16 | 2026-06-06 | 桌面端；自定义限制许可 |
| [easychen/pushdeer](https://github.com/easychen/pushdeer) | 5,022 | 2026-01-16 | 作者明确停止维护；本轮排除，不对全部子组件许可作推断 |
| [wechaty/wechaty](https://github.com/wechaty/wechaty) | 23,090 | 2025-12-21 | TypeScript；Apache-2.0；依赖所选 puppet 能力，不作为首选 |
| [wechatpy/wechatpy](https://github.com/wechatpy/wechatpy) | 4,305 | 2026-05-19 | Python；MIT；微信 API 开发参考 |
| [binarywang/WxJava](https://github.com/binarywang/WxJava) | 33,082 | 2026-09-08 | Java；Apache-2.0；能力参考，现有 Python 后端无需因此另加 Java 服务 |
| [微信官方 miniprogram-demo](https://github.com/wechat-miniprogram/miniprogram-demo) | 7,227 | 2026-09-03 | JavaScript；MIT；小程序交互/API 示例 |
| [Tencent/openclaw-weixin](https://github.com/Tencent/openclaw-weixin) | 841 | 2026-09-08 | TypeScript；MIT；官方 ClawBot 路线，需实际评估主动发送窗口 |
| [easychen/wecomchan](https://github.com/easychen/wecomchan) | 1,751 | 2024-07-30 | MIT；企业微信推送样例，资格描述须刷新 |
| [papercups-io/papercups](https://github.com/papercups-io/papercups) | 6,104 | 2024-02-15 | Elixir；MIT；维护模式，本轮不选为新核心 |

重点候选已核查正式发布：Chatwoot 4.17.1（8 月 27 日）、Apprise 1.13.1（8 月 31 日）、ntfy 2.28.0（8 月 27 日）、aiogram 3.31.0（8 月 25 日）。腾讯插件 GitHub releases 集合本轮为空，这不等于 npm 没有发布；本文没有把它标成“从未发版”。[Chatwoot release](https://github.com/chatwoot/chatwoot/releases/tag/v4.17.1)、[ntfy release](https://github.com/binwiederhier/ntfy/releases/tag/v2.28.0)、[aiogram release](https://github.com/aiogram/aiogram/releases/tag/v3.31.0)
