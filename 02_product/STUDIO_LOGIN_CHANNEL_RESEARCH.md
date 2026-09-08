# 邮箱、微信与手机号登录调研 · 2026-09-08

结论：手机号可以做注册／登录，但发送真实短信通常需要付费通道。能找到少量免计费额度；不能把“认证系统免费”理解成短信免费。现阶段复用已接好的 Resend 邮箱与图纸工具账号，成本和接入工作最少。

下表是服务商公开标准价或免费档，不代表当前商家账号已申请这些权益。美元报价不进行临时汇率换算。

| 方式 | 免费额度／收费条件 | 对当前网站的意义 |
|---|---|---|
| 现有 Resend 邮箱 | 官方 Free 档每月 3,000 封、每天 100 封 | 生产原账号服务已配置 Resend。此次直接复用，客户在手机和微信浏览器里也可以填邮箱收码。未发送真实客户测试邮件。 |
| Firebase / Google Identity Platform 手机短信 | 每天前 10 条发送的短信不计费；加拿大标准单价 USD 0.01／条。Firebase 发真实验证码要求 Blaze 按量付费方案 | 适合先评估少量手机号登录。仍需开通计费、配置地区与限额；验证码重发也消耗条数，不是每天 10 个用户或无限免费。 |
| Twilio Verify | USD 0.05／次成功验证，另计短信通道费；美国短信示例单价不能套用到加拿大 | 商用验证服务可用。免费试用只适合测试：收件号码需先验证、最多 5 个收件号码，不能据此向任意顾客长期免费发码。 |
| 腾讯云短信 | 官方新户活动中，个人首次开通可领 100 条国内短信，领取后 3 个月有效；企业额度/条件有调整 | 这是限时国内短信试用，不能当作发送到加拿大 +1 的免费国际短信通道。需要符合账号认证、签名和模板审核条件。 |
| Supabase Auth | 手机登录仍需配置独立 SMS provider | 即使账号认证层有免费档，也不会自动获得免费的真实短信。当前无需为邮箱登录迁移用户库。 |

依据：[Resend 价格](https://resend.com/pricing)、[Google Identity Platform 价格](https://cloud.google.com/identity-platform/pricing)、[Firebase 手机验证限制](https://firebase.google.com/docs/auth/limits)、[Twilio Verify 价格](https://www.twilio.com/en-us/verify/pricing)、[Twilio 免费试用限制](https://www.twilio.com/docs/usage/tutorials/how-to-use-your-free-trial-account)、[腾讯云短信赠送规则](https://cloud.tencent.com/document/product/382/91668)、[腾讯云当前短信价格说明](https://cloud.tencent.com/document/api/382/8414)、[Supabase 手机登录](https://supabase.com/docs/guides/auth/phone-login)。腾讯云页面正文在当前阅读工具中打开失败，活动说明来自同一官方页面的搜索摘录，实际领取前需在控制台核对资格。

## 微信接入条件

店主已确认没有已认证服务号或已审核网站应用。因此本次不能开通微信官方真实登录。微信个人聊天账号、小红书账号以及现有客服微信号都不能替代网站应用的 AppID／AppSecret。

- 电脑浏览器扫码：申请微信开放平台网站应用，取得审核后可用的 AppID、AppSecret 与回调域名配置。
- 微信内网页：需要具有相应网页授权权限的公众号，配置网页授权域名；认证服务号是常用路径。腾讯当前指南也列出具有 `snsapi_base` 权限且已认证的订阅号场景，实际以账号权限为准。
- 微信官方用户身份返回后，按已验证的 OpenID／UnionID 关联账号；已有邮箱用户应先登录邮箱账号再绑定微信。不能凭填写的微信号、联系人信息或未经校验的临时 code 自动合并账号。
- 原图纸工具的 `/api/v1/user/login` 只是开发用 code 派生身份，当前 Studio 明确不接受该未验证邮箱身份。后续需新增真实服务端 OAuth 验证、绑定和回调防重放，再启用微信选项。

依据：[腾讯 CloudBase 微信登录 v2](https://docs.cloudbase.net/authentication-v2/method/wechat-login)、[腾讯 CloudBase 公众号网页授权指南](https://docs.cloudbase.net/integration/wechat-official-oauth)。微信开发者文档当前阅读工具无法直接打开，采用腾讯维护的当前接入文档交叉核对；没有以第三方示例代替正式认证。

## 手机号后续落地步骤

若决定启用手机号，先选服务商和 +1／+86 覆盖范围，配置预算与短信地区限制。用店主自己的已授权测试号码验证真实送达、微信内验证码输入和重发，再开放。对 Google 网页验证在中国大陆网络中的可用性，本次没有做真机验证，不能承诺所有访客都能访问。

接入时保留现有邮箱用户与预约归属：手机号必须经过服务商验证，再绑定原账号。增加按 IP／号码／总量限流、重发冷却、验证码次数限制、审计与费用监控。本次没有购买短信包、开通付费账号或安装另一套用户数据库。
