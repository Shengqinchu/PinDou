# 登录平台账号与 Authing 操作指南

更新：2026-09-08 Toronto（2026-09-09 UTC）。店主授权使用指定 Outlook 邮箱注册 Firebase 和 Descope，并要求逐步说明 Authing。

## 当前实际状态

| 平台 | 已确认 | 下一步 |
|---|---|---|
| Descope | 已完成邮箱登录，并看到与店主截图一致的 `public-amber-morse`、`Free Plan`；店主完成手机号 OTP 流程向导，未加顾客 MFA | 配置服务端调用所需权限、号码测试与共享身份桥接后才能启用网站手机登录 |
| Firebase | 自动浏览器输入邮箱后被 Google 提示 `This browser or app may not be secure`；没有进入控制台、没有创建项目或开通计费 | 店主用自己的 Chrome 完成 Google 登录；已有 Google 账号与否仍待确认 |
| Authing | 已直接在Codex内置浏览器创建并关联pindou-wechat，托管体验页已生成微信码；费用管理确认B2C免费版、8,000 MAU、有效期无限期 | 店主真实扫码验收；随后完成网站回调和共享身份桥接。手机保持同机邮箱流程，不能套用PC二维码 |

Descope Project ID：`P3J4R1ubICbwLu2OJLsE4UXCVqmP`，由店主从控制台复制提供。本地已写入被 Git 忽略的 `.env` 的 `STUDIO_DESCOPE_PROJECT_ID`。Project ID 是公开标识；没有生成或索取 Management Key、Access Key、密码，没有将邮箱验证链接／会话令牌保存进仓库。

Authing App ID：`6aa0be1ff986e3e847b44a28`；应用地址 `https://pindoupuppy.authing.cn/6aa0be1ff986e3e847b44a28`。店主主动提供的Secret已按授权写入本地明文环境配置。公开端点、实际登录页与尚未完成项见[应用连接记录](STUDIO_AUTHING_CONNECTION.md)。

本轮没有真实短信发送、付费升级、信用卡绑定或网站登录入口变更。官网仍只开放已有邮箱登录。店主的项目注册和代码准备完成不等于手机号登录已经接通。

## Authing：先验证默认“小登录”，再接网站

### 1. 注册与创建应用

1. 打开 [Authing 控制台](https://console.authing.cn/)，点击 **立即注册**。
2. 当前注册页为邮箱验证码注册：输入邮箱、本人完成图形验证码、发送并填写邮件验证码，阅读并勾选服务协议后注册。
3. 进入控制台后使用免费方案。若出现用户池创建，名称使用 `PinDou Puppy`，只创建一套即可。

   店主实际创建页补充：选择 **To C**，取消默认勾选的 **开启体验期**。30天全功能体验到期不升级会停用，不可当作长期免费档；创建后再核对费用管理中的实际版本。[体验规则](https://docs.authing.cn/v2/guides/basics/trial/admin.html)、[用户池版本](https://docs.authing.com/v2/concepts/user-pool.html)
4. 进入 **应用 → 自建应用 → 创建自建应用**。应用名称填 `PinDou Puppy`，认证地址可用 `pindoupuppy`；如已被占用可用 `pindoupuppy-hamilton`。
5. 本项目计划由 Python 后端处理认证结果，使用 **标准 Web 应用**。界面若已创建默认应用，可复用该应用，不需要同时新增多个应用。暂时不要把密钥复制到前端。

   如果注册时勾选“所有应用使用同一域名”，认证地址应在 **设置→基础设置→基础信息** 修改。只把中间随机前缀改为 `pindoupuppy`（占用则 `pindoupuppy-hamilton`）。应用地址自动成为 `https://前缀.authing.cn/APP_ID`，属于正常配置，不需要重新注册。先保留平台生成的体验回调，网站正式回调实现后再替换。[统一认证域名说明](https://docs.authing.cn/v2/guides/faqs/union-domain.html)

依据：[应用类型与创建](https://docs.authing.cn/v2/guides/app/)、[标准 Web 应用配置示例](https://docs.authing.cn/v2/quickstarts/webApp/javaSpringBoot.html)。此处只借用其控制台步骤，网站仍保留 Vue + Python。

### 2. 找到正确的微信模式

进入 **身份源管理／社会化身份源 → 创建社会化身份源 → 微信 → PC 小程序扫码**。它与相邻的 **PC 微信扫码** 是两个选项；我们当前需要 Authing 托管的“小登录”。

官方说明默认使用 Authing 的小程序，自有小程序属于可选的品牌定制路径。[PC 小程序扫码说明](https://docs.authing.cn/v2/guides/connections/social/wechat-miniprogram-qrconnect/)

| 字段 | 本项目填写方式 |
|---|---|
| 唯一标识 | `pindou-wechat` |
| 显示名称 | `微信登录` |
| 小程序 Logo | 可上传 `05_studio/public/studio-brand/xiaogou-shuangji-avatar.png` |
| 页面 | 保持默认 |
| 是否开启私有化部署 | 关闭 |
| 小程序 AppID／AppSecret | 默认托管模式不填自己小程序的凭据 |
| 仅登录模式 | 关闭，使新顾客可以注册 |
| 账号身份关联 | 先保持默认，不开启按昵称／未验证邮箱自动匹配 |
| Callback URL | 平台体验阶段保持可用的默认值／留空；若控制台要求必填，先保留页面，待服务端回调实现后填写准确地址。不能以主站首页代替尚未实现的认证回调。 |

如果选项要求付费、提示默认小程序不可用，或者在关闭私有化部署后仍强制要求自己的 AppID，不继续购买。需要按实际页面核对该账号权限；公开文档不等于新免费账号已经获得生产授权。

### 3. 关联应用与体验

在新建身份源的连接详情中，开启并关联刚才的 `PinDou Puppy` 应用。然后进入该应用，点 **体验登录**，选择微信模式，用本人微信测试能否正常授权并返回 Authing。

先验证平台自己的体验页即可。平台体验成功后，记录 **App ID、认证域名、身份源标识**；它们用于后续网站配置。App Secret 留在控制台／受限环境文件。正式接入还需完成服务端验证、回调、现有账号绑定和预约草稿恢复。

默认“小登录”主要针对电脑展示二维码、手机扫码。微信内打开网站及手机同屏识别还要实测，不能以一次桌面扫码代替全部移动端验收。

店主随后明确要求手机用户同机完成登录。当前手机继续使用已上线邮箱入口，短信接通后加入；“PC小程序扫码”不作为手机必经步骤。微信内网页直接授权需要另一套服务号配置，“微信移动端”则用于原生App。环境矩阵及官方依据见 `../02_product/STUDIO_MOBILE_AUTH.md`。

## Descope：当前向导之后

店主已经完成的配置：B2C → One-time Password → 不增加额外 MFA → 生成手机号输入流程。

接入示例页前端选择 **Vue**，后端选择 **Python**；`Sign Up or In` 合并注册和登录，适合这家店。示例只证明如何嵌入及验证会话，不自动处理我们原生成器的用户 ID、预约权限或 Firebase 配额切换。

后续在 **Authentication Methods → One-time Password** 核对 SMS 渠道，在 **Project** 核对项目设置；保留 **Free Plan** 和默认短信通道。不要为获得免费短信接入自己的付费连接器。官方当前额度是默认短信／语音合计每月100次，超过免费限制需升级；真实发送和重发都会占用额度。[价格页](https://www.descope.com/pricing)

后端模式和密钥权限要一起配置。`Access Keys` 是另一类应用访问凭据，不应直接当作 Descope Management Key 或抄入前端。[后端 OTP](https://docs.descope.com/auth-methods/otp/with-sdks/backend)、[管理密钥及权限](https://docs.descope.com/management)

## Firebase：必须先完成 Google 登录

打开 [Firebase 控制台](https://console.firebase.google.com/)，在本人日常使用的 Chrome 中用指定 Outlook 邮箱登录 Google。

如果这个邮箱尚未成为 Google 账号，可以在 Google 注册中选择 **使用您的电子邮件地址**，继续使用 Outlook，不需要另开 Gmail。姓名、生日及需要的本人验证由店主在 Google 页面完成，不在聊天里提供密码。[Google 官方注册说明](https://support.google.com/accounts/answer/27441?hl=zh-Hans)

登录后创建 `PinDou Puppy` 项目，使用免费 Spark，暂不开 Analytics／付费升级。真实验证短信是否要求 Blaze，仍以该新项目实际权限为准；前期调研发现 Google 两份官方配额文档存在口径差异，详见 `02_product/STUDIO_AUTH_PHASE1.md`。

只有免费资格、额度控制、验证渠道和共享身份桥接都验证完，才开启网站手机／微信注册。当前普通浏览和已上线邮箱预约保持原状。
