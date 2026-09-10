# 自有微信小程序扫码登录

2026-09-10，来源：店主要求“telegram先进行到这里 搞一下小程序吧”，延续自有品牌手机授权页面、共用原账号的要求。

## 已核验

- 当前有效 AppID：`wx9f2b4d171e92a5ef`，微信接口返回名称“双吉拼豆图纸定制”。旧项目配置尾号 95ec 已统一，密钥未进入代码和发布包。
- 开发者工具登录成功，具有该 AppID 权限。真实 `wx.login` 返回的凭证经微信 `jscode2session` 交换成功，不再使用旧的 code 哈希占位身份。
- `getwxacodeunlimit` 接口返回有效图片。未完成认证并未阻断本次已实测接口；这不代表具备网页内嵌、订阅消息或其他接口的全部资格。
- 微信接受本次开发预览包，并成功上传开发版本 **0.1.0**，1,132,472 bytes。尚未设置体验版、提审或正式发布。
- 新增 35 项小程序身份／扫码测试；隔离 Python 缓存后的后端全套 289 项通过。网站中英文、390/1280 宽度、默认密码不请求二维码、自有渠道试用、绑定已有账号入口均通过浏览器检查。
- 模拟器中文／英文确认页、确认／取消结果、过期提示、密码登录页与空表单禁用均已验证并留图。当前开发工具的旧自动化 SDK 元素查询会等待无返回，改由 WXML 已绑定处理函数执行状态测试并核对模拟器截图；这不是手机真实点击验收。
- 开发工具模拟器启动时出现绘制问题，使用其官方 CLI 的 `--disable-gpu` 重启后恢复；没有改变网站或用户系统的动画设置。

## 当前联调状态

Studio **20260910184755-studio-v7** 已部署，366 个文件哈希通过；源代码提交 `e024ae8`。归档 SHA-256：`c728f6055cff4f602526d12f52b61be4857ea980b0f861992c7ef27d10902193`。

服务端目前 `STUDIO_MINIAPP_ENABLED=1`、`STUDIO_MINIAPP_ENV=develop`、`STUDIO_WECHAT_PROVIDER=authing`。线上真实微信凭证交换与自有二维码生成均返回 200，公开默认仍是 Authing。凭据经私有环境文件写入，原环境文件已做 0600 备份。

发布后业务表与发布前备份逐表哈希一致；生成器发布目录、Server 酱启用状态／配额／密钥文件均保持。联调只建立短期扫码与身份验证会话，没有建立任何生产账号绑定或注册新顾客。

**当前必须由微信后台补齐 request 合法域名 `https://pindoupuppy.com`**。启用真实域名检查的模拟器明确返回 `request:fail url not in domain list`；没有以关闭域名检查冒充完成。已请店主在“开发管理 → 开发设置 → 服务器域名”保存，保存后需刷新项目域名信息并继续手机验证。

证据位于工作区忽略目录 `artifacts/miniapp-login/`：`account-check.json`、`wx-code-exchange.json`、`qr-api-check.json`、`live-probes.json`、`upload-info.json`、`backend-tests-fresh.txt`、`web-checks.json`、`native-checks.json`、`preservation.json` 及原生截图。凭据、原始登录 code、openid、session_key 与浏览器扫码状态不写入这些报告。

## 产品与账号

原生页面 `pages/auth/studio-confirm` 使用店主的小狗图标和 logo，展示网站域名、校验码、确认及取消按钮；没有 Authing 共享小程序的个人中心。原生登录页 `pages/auth/studio-login` 使用账号密码，并可显式绑定当前微信或创建新账号；邮箱验证码只引导到网站原有找回流程。

网站默认密码登录、注册／登录／微信登录标签不变，选择微信标签才生成二维码。当前默认提供方继续为 Authing；仅在服务端自有渠道已配置时，`/account?wechat_provider=miniapp` 启用试用入口。

二维码场景值与浏览器登录状态分离。微信真实身份由服务端交换，手机短期凭证只留在页面内存；原浏览器还须持有 HttpOnly Cookie、匹配 Origin 和一次性状态才能领取登录结果。有效期 5 分钟，手机证明有效期 10 分钟；拒绝、过期、其他微信抢扫、错浏览器及重复领取均拦截。

扫描和确认不会自动创建新账号。已有账号通过已签名的原账号登录绑定，保持原 user_id、图纸、预约、积分和时长。Authing-only 老客应先在网站按原方式登录，再进入试用链接绑定当前微信；不按昵称、邮箱或手机号静默合并。

新账号由既有 loopback 签名桥创建，身份使用 `pindou-native-wechat-v1|appid|openid` 的域隔离哈希；内部兼容现有 `wechat_authing_` ID 命名空间，生成器服务及数据库结构不改。166 注册积分依照原钱包幂等记账。

## 配置与切换

服务私有 EnvironmentFile：`/opt/pindou/studio/shared/.env`。新增变量：

| 变量 | 含义 |
|---|---|
| STUDIO_MINIAPP_APP_ID | 当前自己的 AppID |
| STUDIO_MINIAPP_APP_SECRET | 当前自己的密钥，只在私有环境中 |
| STUDIO_MINIAPP_ENABLED | 默认 0，完整配置后才启用试用接口 |
| STUDIO_MINIAPP_ENV | develop / trial / release，与微信版本状态一致 |
| STUDIO_WECHAT_PROVIDER | 默认 authing，公开切换时才设 miniapp |

独立新增 `studio_miniapp_identities`、`studio_miniapp_tickets`、`studio_miniapp_flows`；旧 Authing 表和预约、账本、通知配置保持。访问令牌仅在服务器内存短期缓存，不落数据库，不记录 URL 密钥或微信 session_key。

开发版本期间使用 `develop`；开发者/体验成员权限由微信控制。设置体验版后用 `trial`；正式审核发布、真机回归完成后才设 `release` 并切换网站默认提供方。回退时将 `STUDIO_WECHAT_PROVIDER=authing`，必要时停用新接口；保留身份关联表以免回退丢失绑定。

## 上线前手机核验

1. 微信开发管理配置合法 request 域名 `https://pindoupuppy.com`；图纸上传／下载使用相应合法域名，启用域名检查验收。
2. 开发预览里核对中文/英文、输入框与底部按钮，以及微信内取消／过期／重新打开。
3. 网站二维码由开发者手机扫描，核对四位码、确认返回原浏览器；先用已有网站账号绑定，再复验密码和扫码指向同一账号。
4. 上传开发版本、设置体验成员与体验版，完成真机回归；核验主体、实际类目、隐私声明和所需接口，再提审发布。
5. 顾客微信订阅通知是后续独立功能，不把扫码登录授权当作订阅授权。Telegram 当前暂停，Server 酱既有提醒保持运行。
