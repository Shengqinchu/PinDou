# 第一阶段登录方案与接入准备 · 2026-09-08

> 后续进展：店主已完成 Descope Free 项目 `public-amber-morse` 的手机号 OTP 向导，本任务也已用指定邮箱登录确认同一项目。Project ID 已写入本地受忽略配置。Firebase 自动登录被 Google 安全检查拦截，尚未创建项目。Authing 已配置为 `pindoupuppy.authing.cn`，应用参数已保存，微信身份源已创建和关联，托管体验页已生成二维码；控制台确认B2C免费版、8,000 MAU、有效期无限期。真实扫码、网站回调和共享账号桥接未完成。当前待办见 `../07_ops/STUDIO_AUTH_ACCOUNT_SETUP.md` 和 `../07_ops/STUDIO_AUTHING_CONNECTION.md`，手机同机登录边界见 `STUDIO_MOBILE_AUTH.md`。下文“账号未创建”描述前一轮决策时的状态。

来源：店主要求“Firebase 每天优先，用完转 Descope，使用免费额度”，并希望先采用第三方微信登录服务或开源项目；随后确认 Firebase／Descope 账号均未创建，也没有自己的小程序／已认证公众号。

当前结论：保留共享邮箱登录；短信按 Firebase → Descope → 邮箱的顺序准备。微信优先核验 Authing 托管的“小登录”，wxAuth 作为免费备选。第三方托管小程序能省去自建小程序的步骤；普通 OAuth 开源库仍需要微信应用凭据。

## 短信免费额度：已经确认与仍待验证

| 项目 | 官方公开信息 | 对本项目的影响 |
|---|---|---|
| Google Identity Platform 价格 | 每日前 10 条短信不计费，加拿大 USD 0.01／条；按发送数计，不按成功登录计 | 重发也用额度；用完必须主动停发／换通道，不能把预算通知当硬停止。[价格](https://cloud.google.com/identity-platform/pricing) |
| Firebase Authentication | 2026-09-08 更新的限制页要求真实验证短信使用 Blaze | 不能保证新 Firebase 项目在不绑定计费的情况下能发送。[限制页](https://firebase.google.com/docs/auth/limits) |
| Google Identity Platform 配额 | 2026-09-03 更新页仍列 Instrumentless 每天 10 条 | 与 Firebase 页面存在产品／文档口径差异。优先检查新项目是否有无计费短信资格，不先承诺或自动开通 Blaze。[配额页](https://docs.cloud.google.com/identity-platform/quotas) |
| Descope Free | 7,500 MAU；默认短信与语音合计 100 次／月；免费档超过限制需升级 | 不接自己的付费短信连接器、不购买短信包。100 次为项目总额，测试与重发也需计入。[价格](https://www.descope.com/pricing) |
| Descope 生产条件 | 默认 OAuth 应用仅供测试；后端调用可限制公开 SDK／API 访问 | 默认 OAuth 额度不能视为生产微信登录资格；手机号发送必须限制入口。[上线指南](https://docs.descope.com/how-to-deploy-to-production) |

短信免费的范围是上述发送额度，不代表云函数、数据库或其他云资源永远免费。加拿大号码的送达速度、地区限制、重发和实际账单仍需在店主账号上验证。本轮没有创建账号、启用计费或发送任何真实短信。

## 已编写的准备代码

`06_studio/sms_policy.py` 是独立的 SQLite 配额账本；目前未注册 HTTP 路由，也未进入生产打包清单。`customer_auth.py` 继续返回 `phone=false`、`wechat=false`，不会出现点了不能使用的登录入口。

- 服务端原子预留名额，按固定优先级选通道；缺少已验证配置时走邮箱。调用者传入顺序不能反转店主指定的优先级。
- 同一个请求重复点击、服务重启、网络响应不明，都不能获得第二次发送许可。主动重发是新请求，重新计数。
- 验证码发出后固定回到原平台验证，不能在输错码／超时后拿另一个平台验证。失败和不明状态不自动退款，避免重复发送和费用误计。
- 账本仅接受不透明请求编号和服务端带密钥哈希，不保存手机号或验证码。它不能代替供应商令牌验证、号码/IP 限频或防机器人措施。
- 官方页面尚未明确本项目的额度重置时区。准备代码暂用 **滚动 25 小时最多 10 次／滚动 32 天最多 100 次** 的保守边界，避免按 Hamilton 午夜重置而跨供应商账期超额。这比店主期望的自然日／月严格；新账号核实边界后再调整，不能把当前准备代码称作已完成每日／每月生产接入。

本地 10 项测试覆盖 150 个并发请求、10→100→邮箱、重启重放、原通道验证、超时、失败不返额和时段边界；共享邮箱账号另有 11 项回归通过。全部使用隔离数据库，没有调用短信网关。

真正保证 Firebase 费用需要覆盖**所有**发送入口。浏览器 API key 是公开配置，单纯在网站按钮或本地账本数到 10 就停，仍可能被绕过。Google 提供 Node.js `beforeSmsSent` 阻断钩子，但需要 Identity Platform；开通后还需验证钩子覆盖注册、登录、重发／MFA，拒绝时确实不发送，以及函数故障时能停止发送。[阻断钩子](https://firebase.google.com/docs/functions/auth-blocking-events)

## 微信平台比较

| 候选 | 自己是否需要小程序／公众号 | 费用证据 | 决策 |
|---|---|---|---|
| **Authing“小登录”** | 托管模式用 Authing 的小程序；以后可切自有小程序 | 当前价格页列免费 8,000 MAU、1 个社交连接、1 个应用；基础版从 RMB 139／月。免费短信只是共计 10 条，不与 Firebase／Descope 额度混淆 | **优先核验**。V3 API 仍提供“小程序扫码→查询状态→ticket 换令牌”；但新免费账号是否开放托管“小登录”和生产使用，必须看实际控制台权限，不能仅凭价格表保证。[V3 API](https://api.authing.cn/)、[当前价格](https://www.authing.com/pricing)、[配置方式](https://docs.authing.cn/v2/guides/app/config-login-methods.html) |
| **wxAuth** | 使用其托管扫码接口，无需先部署自己的小程序 | 首页明确“目前免费”，保留以后收费可能；开发文档可读 | 免费备选。个人维护，无本轮可验证的服务 SLA；需用真实账号测扫码、后端换用户身份和加拿大网络体验。[官网](https://wxauth.com/)、[开发文档](https://wxauth.com/doc/) |
| 彩虹聚合登录 | 提供统一第三方登录接口；官网称注册后可接入 | 公开页未取得可确认的当前微信收费表；实际注册页要求手机号验证码 | 保留候选，不采用旧文章“几元永久”当报价。[官网](https://u.cccyun.cc/)、[注册页](https://u.cccyun.cc/user/reg.php) |
| 蓝天聚合登录 | 官网称统一接口覆盖微信等渠道 | 未取得当前可复核的微信套餐价格及免费限额 | 信息不足，不作为首发唯一登录通道。[官网](https://oauth.hiltyun.com/) |
| juhedenglu.cn | 宣称聚合微信登录 | 首页价格和公告同时出现免费、年费及暂停对外／清除免费用户等不一致信息 | 暂不选用，不能凭首页低价作为长期保障。[官网](https://www.juhedenglu.cn/) |

托管扫码与微信内网页一键授权是两种体验。桌面扫码较自然，手机浏览器／微信内页面能否直接拉起或识别同屏二维码，需要按所选服务实测；不能只测桌面就宣称手机微信登录已适配。首阶段保持邮箱入口作为通道故障时的回退。

Authing 旧版说明明确：托管“小登录”和未来自己的微信主体的 UnionID 不相同。因此现在就应使用内部用户 ID，记录 `(provider, app_id, subject)` 绑定，并允许顾客验证后绑定邮箱，避免以后迁移丢账号。[托管与自有小程序区别](https://old-docs.authing.cn/scan-qrcode/wxapp-qrcode/private-wxapp.html)

## GitHub 实际代码与维护情况

2026-09-08 Toronto（抓取时间为 09-09 UTC）读取官方 GitHub API 的仓库状态、许可证与 README，并检查对应接入文档／实现。星数是此时快照，不代表质量保证。

| 项目 | 技术／许可／星数／最近 push | 能否免去自己的微信账号 |
|---|---|---|
| [Authing/wechat-eco-solution](https://github.com/Authing/wechat-eco-solution) | JS 示例；MIT；17；2022-08-11 | 托管“小登录”有用，但示例较旧，生产以当前 V3 API 为准；开源示例本身不授予 SaaS 免费权益 |
| [Casdoor](https://github.com/casdoor/casdoor) | Go/React；Apache-2.0；14,370；2026-09-07 | 自建身份服务；其[小程序示例](https://github.com/casdoor/casdoor-wechat-miniprogram-example)明确需要自有 APPID／APPSECRET；不能替代微信申请 |
| [Logto](https://github.com/logto-io/logto) | TypeScript；MPL-2.0；14,507；2026-09-09 UTC | [微信 Web 连接器](https://docs.logto.io/integrations/wechat-web)要求创建微信网站应用并配置凭据；自建还增加一套服务维护 |
| [JustAuth](https://github.com/justauth/JustAuth) | Java；MIT；17,517；2026-04-16 | 多平台 OAuth 库，配置 clientId/clientSecret；当前 Vue + Python 站引入 Java 仅为微信不划算 |
| [Auth.js](https://github.com/nextauthjs/next-auth) | TypeScript；ISC；28,366；2026-07-22 | [微信 provider 实现](https://github.com/nextauthjs/next-auth/blob/main/packages/core/src/providers/wechat.ts)仍使用 AUTH_WECHAT_APP_ID/SECRET；不是共享微信应用服务 |
| [songquanpeng/wechat-server](https://github.com/songquanpeng/wechat-server) | Go；MIT；530；2023-12-19 | 公众号消息／验证码路径，需要自己的公众号；仓库多年未 push。可供研究，不能直接用默认配置部署 |

这些开源项目有接入参考价值。对当前“没有微信开发账号、想低成本首发”的条件，托管“小登录”比再搭一个身份服务器更合适；以后业务扩大再决定自有微信应用和自托管服务。

## 公众号是否更省事

应区分普通公众号、个人订阅号消息交互和已认证服务号网页授权。申请一个公众号不等于获得网站所需的微信 OAuth 权限。Authing 的当前公众号网页授权接入指南要求**服务号、微信认证、AppID/AppSecret 和授权域名验证**，仍有主体及配置步骤。[官方接入指南](https://docs.authing.cn/v2/reference/sdk-for-weixin-official-account.html)

个人订阅号的消息验证码路线可以作为以后研究方向，但体验是进入公众号、发消息／取验证码、返回网站，仍需自己的公众号和可信的消息签名校验。本轮腾讯开发者文档直连读取失败，未重新确认加拿大主体／个人注册资格、具体材料与认证价格，所以不把固定“300 元／年”或“个人一定可申请服务号”写成结论。现阶段无需为登录专门推进公众号申请。

## 接入顺序与当前待办

1. **已完成**：两张英文 Logo、复制区域、媒体编辑入口、文案归档和响应式检查；短信配额准备代码与隔离测试；本轮平台和 GitHub 调研。
2. **等待店主创建账号**：Firebase/Google Cloud 项目与 Descope Free 项目；微信优先创建 Authing 免费应用，查看“微信 PC 小程序扫码／小登录”权限。只创建项目，先不启用收费计划。若 Authing 免费账号不提供托管能力，转 wxAuth 验证。
3. **配置齐全后实施**：服务端适配器、供应商层硬停发、令牌校验、重置时间、地区许可、密钥管理；Descope 禁止无管理权限的公开发码入口。
4. **共享账号桥接后开放入口**：当前账号由生成器服务签发 JWT，Studio 不维护第二套密码库。手机号／微信验证后要由可信服务绑定或创建内部身份，继续签发兼容 JWT；已有邮箱必须验证后才可绑定，不以昵称或未验证邮箱自动合并，不捏造邮箱占位。
5. **真实验证**：店主控制的 +1 号码、收到与重发、两供应商边界、错误码不重复发送、手机同屏扫码、Windows Chrome、iOS/微信真实设备、预约草稿保留。只在实际账号上验证通过后把对应登录入口改为开启。

账号密钥存本地／服务器配置文件，不提交 Git、不放前端。本次店主主动提供的Authing凭据按其授权保存在本地明文 `.env`。当前完成的是代码准备、应用配置记录和公开端点核验，**真实手机号与微信登录尚未接通**。
