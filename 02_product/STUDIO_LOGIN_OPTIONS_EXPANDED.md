# 登录渠道扩展调研 · 2026-09-08

店主补充：“十条也够了，再看看有没有别的优惠、方法、平台，全网搜一下。微信登录只能靠开放平台？没有别的办法？”

结论：微信有网站应用以外的登录路径，之前只围绕网站 OAuth／认证服务号说明，范围过窄。个人公众号消息验证码、自有小程序扫码、第三方提供的小程序扫码，都值得考虑。短信方面，Firebase 的每天 10 条免计费仍匹配当前需求；新增确认 Descope 每月 100 次短信／语音发送，以及自有 Android 手机网关等选择。

本轮检查服务商当前价格／试用页、官方接入文档和开源实现；只调研，没有注册第三方账号、申请认证、领券、开通计费、发短信或改动线上登录。美元、欧元与人民币报价分别保留，不与网站 CAD 标价混用。

## 持续额度与自建方法

| 平台／方式 | 已确认的额度 | 条件、局限与判断 |
|---|---|---|
| Firebase / Google Identity Platform | 每天前 10 条验证短信免计费；加拿大标准价 USD 0.01／条 | 真实短信需 Blaze 按量计费方案。免费的是发送条数，重发也计入；按日计算，不是每月可任意集中使用的 300 条。当前最合适的首选。 |
| Descope | Free 档 7,500 MAU，自带短信／语音发送合计每月最多 100 次 | 达到额度后该通道无法继续注册／登录，需要自带短信连接器或购买套餐。适合每月少量、某几天集中的需求。加拿大实际投递还需自己的测试号码验证。 |
| textbee | 免费云档 1 台设备，每天最多 50 条、每月最多 300 条；无需信用卡 | 这是手机网关软件额度。短信由自己的 Android + SIM 发出，套餐费用、自动发送用途的运营商条款和常在线维护另算，不能当作平台送 300 条运营商短信。 |
| SMSGate | Apache-2.0 开源；可本地或自建服务器 | 同样通过自己的 Android + SIM 发短信。适合有闲置设备、愿意维护的人；软件免费不代表手机套餐免费。 |
| Textbelt | 公共试用 key 每天 1 条免费 | 低于我们期望的每日 10 条；免费路由的加拿大实际送达未验证。它的自建开源版依赖运营商 email-to-SMS 网关，不等同于成熟商业短信通道。 |

来源：[Google 价格](https://cloud.google.com/identity-platform/pricing)、[Firebase 短信限制](https://firebase.google.com/docs/auth/limits)、[Descope 价格](https://www.descope.com/pricing)、[Descope 生产接入说明](https://docs.descope.com/how-to-deploy-to-production)、[textbee 价格与工作方式](https://textbee.dev/)、[SMSGate](https://sms-gate.app/)、[SMSGate 工作模式](https://docs.sms-gate.app/getting-started/)、[Textbelt](https://textbelt.com/)。

按 Google 当前加拿大短信单价推算，仅计算短信发送费用：

| 假设使用量 | 计算 | 估算短信费用 |
|---|---|---|
| 每天 10 条，连续 30 天 | 每天均在免计费范围 | USD 0 |
| 每天 20 条，连续 30 天 | 10 × 30 × USD 0.01 | USD 3 |
| 某一天集中发 300 条 | (300 − 10) × USD 0.01 | USD 2.90 |

这是使用量示例，不是固定包月价或全部服务账单。实现时需要控制发码频率、服务端／平台总量及重发；预算通知不能被当成已经实现了硬停发。额度不足或通道不可用时，保留邮箱登录。

## 其他优惠、试用与排除理由

| 平台 | 当前查到的情况 | 对我们是否有用 |
|---|---|---|
| 阿里云国际站 SMS | 当前产品页仍展示新户 100 条免费试用 | 可作为试用候选；领取资格、有效期和可用目的地需在领取页核验，不能按长期免费算。国际短信产品覆盖加拿大，但本轮未验证试用包到加拿大的具体权益。 |
| Twilio | 当前为 30 天试用，Messaging 含 100 条 SMS；试用收件号码要预先验证，最多 5 个；限注册所在国家 | 适合验证接口，不适合作任意新顾客的持续免费发码服务。旧的美元余额型试用说法不宜继续套用。 |
| Vonage | 开发文档列出 EUR 2 demo credit，最多 10 个目的号码，短信附带 demo 提示 | 短期测试；升级需充值。 |
| Plivo | 当前文档列出前 3 周试用额度 | 未取得固定赠送金额；不能当作长期免费配额。 |
| Telnyx | 文档说明试用只能与验证过的号码收发；帮助页同时说明目前没有统一免费赠额活动 | 不能采信旧文章里固定送若干美元的承诺。 |
| Sinch | 免费试用账号最多 5 个验证号码；另有 Engage 移动应用 14 天／25 条试用 | Engage App 的优惠不能直接当成 Verify API 给网站的免费短信。 |
| 腾讯云国内 SMS | 个人新主体首次开通 100 条；企业 200 条；有效期 3 个月 | 国内包不适用于加拿大 +1。2026-03-24 企业赠送量已调整，旧的 1,000 条说明过时。 |
| 腾讯云国际 SMS | 当前产品页明确不提供免费测试额度；国际计费页说明不支持代金券 | 通用云优惠券不能据此当作国际短信余额。 |
| MSG91 | demo 只能发测试内容；另有面向印度初创的每月最高 50,000 credits、6 个月优惠 | 不能假设加拿大实体小店符合该初创计划。OTP Widget 的 Free Plan 名称也不能直接推导免费加拿大短信条数。 |
| Bird Verify | Verify 验证逻辑无额外平台费，发送按所用通道收费 | “Verify 免费”不等于 SMS 免费；未查到明确可持续的加拿大免费短信额度。 |
| Stytch | 2024 官方文章说美加 OTP 免费，但当前价格 FAQ 说明 SMS／WhatsApp 费用按供应商成本透传，未明确美加豁免 | 信息有冲突，不能仅凭旧文承诺加拿大短信免费；应取得当前账号套餐确认后再考虑。 |
| Supabase | Phone Login 仍要求配置短信供应商 | 免费账号认证层不赠送同等数量的真实短信。 |

来源：[阿里云 SMS](https://www.alibabacloud.com/en/product/short-message-service)、[阿里云当前接入流程](https://www.alibabacloud.com/help/en/sms/getting-started/get-started-with-sms)、[Twilio 试用](https://www.twilio.com/docs/usage/trials)、[Vonage demo 条件](https://developer.vonage.com/en/account/guides/dashboard-management)、[Plivo 试用](https://www.plivo.com/docs/faq/account/plans)、[Telnyx 试用限制](https://developers.telnyx.com/docs/account-setup/using-trial-account)、[Telnyx 赠额说明](https://support.telnyx.com/en/articles/5295540-how-to-sign-up-for-a-telnyx-account)、[Sinch 试用账号](https://support.sinch.com/hc/en-us/articles/53501378504467-How-to-sign-up-for-your-free-Sinch-account)、[Sinch Engage App](https://support.app.sinch.com/hc/en-us/articles/14635506484751-Mobile-app-Free-trials)、[腾讯云国内价目](https://cloud.tencent.com/document/api/382/8414)、[腾讯云国际产品](https://intl.cloud.tencent.com/zh/products/sms)、[腾讯云国际计费](https://intl.cloud.tencent.com/pricing/sms)、[MSG91 demo 限制](https://msg91.com/help/text-sms/why-am-i-unable-to-send-an-sms-with-the-content-of-my-choice-i-get-demo-content-repeatedly)、[MSG91 初创计划](https://msg91.com/guide/dazzle-your-clients-with-sms-for-startups-offer)、[MSG91 Widget](https://msg91.com/help/sendotp/how-to-integrate-the-new-login-with-otp-widget/msg91-otp-widget-subscription-)、[Bird Verify](https://bird.com/products/verify/pricing)、[Stytch 当前价格 FAQ](https://stytch.com/pricing)、[Stytch 旧文](https://stytch.com/blog/user-linking-and-provider-failover-with-stytch/)、[Supabase](https://supabase.com/docs/guides/auth/phone-login)。Stytch 当前 FAQ 通过浏览器展开读取，不只依赖搜索摘要。

另外核查了学生／新户优惠：Google Cloud 符合条件的新户有 USD 300、90 天试用，需满足未领取过、未曾付费使用相关服务等资格；服务覆盖与短信 SKU 抵扣不能在未核对账单条款前保证。GitHub Student Developer Pack 的当前官方目录未找到 Twilio，网上旧的“学生送 USD 50”不能作为当前确定可领取的福利。[Google 试用 FAQ](https://cloud.google.com/signup-faqs)、[GitHub 当前学生包](https://education.github.com/pack)

## 微信不只网站应用一条路

| 路线 | 店主需要什么 | 顾客的操作 | 判断 |
|---|---|---|---|
| 微信开放平台网站应用 | 已审核的网站应用、相应开发配置 | 扫码并授权 | 原生网站登录路径，但并非唯一选择。 |
| 个人公众号消息验证码 | 自有公众号（原订阅号）、管理员实名、可用消息推送／被动回复能力 | 扫公众号 → 发“验证码” → 把回码填回网站 | 可行，免去网站应用审核。操作多一步，但适合低成本起步。 |
| 自有小程序扫码桥接 | 注册并发布自己的小程序，配置后端／域名或云托管等 | 扫小程序码 → 在小程序确认登录 | 可行，微信身份通过 wx.login + 服务端 code2Session 获取；需要额外小程序开发和审核。 |
| 认证服务号网页授权 | 具备网页授权权限的服务号及域名配置 | 在微信内确认授权 | 适合微信内网页体验；这是公众平台业务路径，不等同于网站应用审核。 |
| 第三方小程序扫码 | 如 Authing“ 小登录 ”或 wxAuth 的开发者账号与接口配置 | 扫第三方提供的小程序码并确认 | 可减少自建工作，但要核实服务费用、品牌展示、身份数据控制与可用性。不能默认永久免费。 |

### 本轮直接核实到的官方细节

微信的新文档已把公众号（原订阅号）与服务号分开，开发配置迁移到了“微信开发者平台”。店主截图里的“微信开放平台网站应用”与这个管理入口、微信公众平台不是同一项申请。

官方迁移说明写明：个人主体启用 AppSecret 时需要管理员实名；非个人主体有主体认证要求。官方消息文档确认，用户发给公众号的消息会推送给开发者服务器，携带该公众号下的用户 OpenID，并可通过被动回复回应。因此可以基于这些能力实现自己的登录验证码流程。这里是基于官方消息能力的应用设计，不是把网页 OAuth 权限授予未认证账号。

参考：[公众号开发入口迁移与实名说明](https://developers.weixin.qq.com/doc/subscription/guide/dev/migration.html)、[消息与事件推送](https://developers.weixin.qq.com/doc/subscription/guide/dev/push/)、[接收普通消息](https://developers.weixin.qq.com/doc/subscription/guide/product/message/Receiving_standard_messages.html)、[被动回复](https://developers.weixin.qq.com/doc/subscription/guide/product/message/Passive_user_reply_message.html)。本轮已通过真实浏览器读取正文，纠正上一轮“微信官方文档无法打开”的局限。

公众号取码登录可按“用户在公众号请求一次性验证码 → 服务器把验证码与已验证的 OpenID 绑定 → 用户在网站输入验证码 → 服务端一次性兑换本站会话”实现。应使用加密消息推送、校验消息来源、短有效期和严格尝试次数；不能信任浏览器传来的 OpenID，不能把客服微信号或静态回复当成身份证明。

小程序登录的官方能力是 wx.login 获取一次性 code，服务器通过 code2Session 得到 OpenID。UnionID 只在满足绑定条件时返回；登录我们共用的本站用户库不必把获取 UnionID 作为第一步。把微信身份关联到已有账号时仍需登录／验证原账号，不能凭相同昵称自动合并。[小程序登录](https://developers.weixin.qq.com/miniprogram/dev/framework/open-ability/login.html)

自有小程序并非只填一个 AppID：官方网络规范要求 request 等通讯域名使用 HTTPS 且经过 ICP 备案；微信云托管可免配置通讯域名，但会引入对应后端部署。本轮没有核验 pindoupuppy.com 是否满足小程序通讯域名条件，也没有改变现有服务器。[小程序网络规范](https://developers.weixin.qq.com/miniprogram/dev/framework/ability/network.html)

Authing 当前 V3 API 仍明确支持其自有小程序扫码流程，分为生成二维码、查询状态、用 ticket 换 token；其旧文描述可使用平台“小登录”而不自建小程序。当前套餐是否含此功能及费用尚未在账户内确认。[Authing V3 API](https://api.authing.cn/)、[Authing 小登录说明（旧版文档）](https://old-docs.authing.cn/scan-qrcode/wxapp-qrcode/)

wxAuth 官网搜索快照称当前免费，并保留以后收费的可能。本轮直接打开超时，没有进行真实扫码，故只列为候选，不作为已验证可用于生产的免费服务。[wxAuth 官网](https://wxauth.com/)

## 代码参考核查

以下 Stars 与仓库时间为本轮 GitHub API 读取值，不是项目质量保证。

| 项目 | 功能／技术 | Stars；最后推送 | 使用判断 |
|---|---|---|---|
| [songquanpeng/wechat-server](https://github.com/songquanpeng/wechat-server) | 公众号取码后换 OpenID；Go + Gin；MIT | 530；2023-12-19 | 已读消息路由、消息处理和验证码存取代码，可证明方案不是空想。只能参考，不能直接原样部署。 |
| [likeyun/Xcx_ScanLogin](https://github.com/likeyun/Xcx_ScanLogin) | 小程序码 scene + 确认登录 + 网页查询；PHP + 小程序 | 54；2024-04-18 | 可参考交互流程；API 元数据未见许可证，README 示例将 token 放回调 URL，不能原样套用。 |
| [android-sms-gateway/server](https://github.com/android-sms-gateway/server) | Android SMS 后端；Go；Apache-2.0 | 187；2026-09-08 | 维护较活跃，适合自建手机网关的候选。 |
| [textbee/textbee](https://github.com/textbee/textbee) | Android SMS 云／自建网关；TypeScript；MIT | 3,086；2026-08-22 | 免费额度与手机套餐成本需分开。 |

wechat-server 核查固定在 `13d0e3264ced535f424c586dd6465f0346e38e1a`。静态阅读发现 `POST /api/wechat` 消息处理没有对应的消息验签，只有 GET 配置验证校验签名；数字验证码使用 math/rand。未测试任何线上实例，也未安装该项目。若采用公众号路线，应在我们自己的认证服务中实现正确的消息验证与安全随机数，而不是直接复用整套旧服务器。[路由](https://github.com/songquanpeng/wechat-server/blob/13d0e3264ced535f424c586dd6465f0346e38e1a/router/api-router.go)、[消息处理](https://github.com/songquanpeng/wechat-server/blob/13d0e3264ced535f424c586dd6465f0346e38e1a/controller/wechat.go)、[验证码](https://github.com/songquanpeng/wechat-server/blob/13d0e3264ced535f424c586dd6465f0346e38e1a/common/verification.go)

## 推荐顺序与下一步

1. 手机号：Firebase 每天 10 条 + 现有邮箱备用，符合店主已确认的数量。Descope 是每月 100 条的替代方案。采用一个主短信通道，方便统一处理验证状态与费用。
2. 微信：愿意运营公众号时，优先核实个人公众号的管理员实名及消息推送权限，实施取码登录；希望更接近扫码确认的体验时，再选自有小程序或核实 Authing 小登录套餐。
3. 若有闲置 Android 与适用的 SIM，可试验 SMSGate／textbee。没有现成设备时，额外购机与维护未必值得。
4. 真正接入手机号／微信时，新的已验证身份需要关联现有账号与预约归属。不能只把当前 `/auth/options` 改为 true，也不能复用旧开发版微信登录占位接口。本轮线上仍只开放已完成的邮箱渠道。

候选服务的短信真实送达、加拿大号码路由、微信内跨页面返回和账户套餐资格，都还没有用店主账号实测。上述明确免费额度来自当前官方公开资料；账号特定优惠不视为已经领取。
