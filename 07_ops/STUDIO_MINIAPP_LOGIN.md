# 自有微信小程序扫码登录

2026-09-10，来源：店主要求“telegram先进行到这里 搞一下小程序吧”，延续自有品牌手机授权页面、共用原账号的要求。后续“做对于小程序的适配吧 ui”对应下方 0.1.2。

## 0.1.2 原生界面适配

已上传微信开发版本 **0.1.2**，微信 CLI 返回包体 **1,262,636 bytes**。本次没有提交正式审核或发布，也没有改线上网站的默认微信提供方、服务器配置或通知渠道。

- `StudioShell` / `StudioBrand` / `StudioGlyph` 与共享 `studio-native.ts` 负责手机布局、原始 logo 视口、按钮反馈、语言与键盘生命周期。保留原始图片字节；白底、灰黑文字、浅蓝按钮，品牌可以按压捏捏。
- 中文标题用 12,000 bytes 的小赖手写子集；英文 DM Serif Display 与 Outfit 一起内嵌 WXSS，避免首次打开依赖字体网络请求。字体授权与 SHA-256 在 `05_frontend/src/static/studio/`，重建入口 `05_frontend/scripts/build-studio-fonts.py`，不打包完整 TTF。
- 原生默认页是账号密码，三个标签为注册／登录／微信登录。仅在选择微信或提交表单后获取微信会话；输入保留，支持显示密码、键盘下一项／完成、错误重试。注册复用已存在的网站密码注册接口；若当前微信已绑定，创建账号前拒绝，避免产生多余账号。邮箱验证码没有加入登录。
- 扫码确认显示四位号码与绑定账号；确认、取消、过期分别呈现。手机证明过期时重新获取，不继续展示无效确认按钮。
- 新增 `pages/auth/studio-account`，已登录默认进入账户概览，读取既有 `/auth/me`、`/auth/wallet` 的当前账号数据，显示时长、积分和预约称呼／联系方式。保留图纸工具入口，旧原生 `pages/user/me` 兼容跳转；原图纸 H5 模板保留。资料编辑、预约操作仍使用网站已有流程，本次不另建账本或账户系统。
- 文案全部复用已批准的 `miniapp`、`account`、`wallet`、`booking-profile`、`pages-Visit`、`components-BrandMotif` 模块；69 个模块的文案校验通过，无批准哈希更新。

验证：原生与 H5 编译通过；微信模拟器中默认不请求微信会话、输入保留／密码可见、注册校验、绑定后进入账户、确认／取消／过期等初步 7 组状态检查通过，最终包另有 6 组原生回归，包括已绑定微信不能先创建第二个账号、手机证明过期后的重试。原生实际测得输入 16px／52px 高，主按钮 58px 高。隔离的 Chromium／WebKit 编译页面覆盖 320×568、375×667、390×844、430×932、667×375 中英文登录／注册，共 28 组布局检查通过；标题与按钮过渡期间和静止状态分别核对。所有身份／账户测试使用 `.invalid` 模拟数据，没有注册真实测试账户或改动余额。

限制：本轮微信开发者工具的 `Tool.screenshot` 多次没有返回，工具窗口截屏为空白；实际原生页面状态和布局查询可用。`web-login-zh.png`、`web-login-en.png`、`web-account-zh.png` 是同一组件的 H5 视觉预览，不冒充原生截图。尚未完成 **0.1.2 真机键盘和外观验收**；此前 0.1.1 真机扫码登录成功的结论仍只对应此前版本。

证据：`artifacts/miniapp-ui/native-checks.json`、`native-final.json`、`responsive-checks.json`、`upload-info.json` 和预览图片。输入采用平台的 `adjust-position`、`cursor-spacing`，参考 [DCloud input 文档](https://uniapp.dcloud.io/component/input.html)，最终软键盘表现仍须以真机为准。

## 已核验

- 当前有效 AppID：`wx9f2b4d171e92a5ef`，微信接口返回名称“双吉拼豆图纸定制”。旧项目配置尾号 95ec 已统一，密钥未进入代码和发布包。
- 开发者工具登录成功，具有该 AppID 权限。真实 `wx.login` 返回的凭证经微信 `jscode2session` 交换成功，不再使用旧的 code 哈希占位身份。
- `getwxacodeunlimit` 接口返回有效图片。未完成认证并未阻断本次已实测接口；这不代表具备网页内嵌、订阅消息或其他接口的全部资格。
- 微信已接受开发预览与代码上传。首次 0.1.0 为 1,132,472 bytes；修正版 **0.1.1** 为 1,128,956 bytes，已上传。店主已将版本设为体验版；尚未正式提审或发布。
- 新增 35 项小程序身份／扫码测试；隔离 Python 缓存后的后端全套 289 项通过。网站中英文、390/1280 宽度、默认密码不请求二维码、自有渠道试用、绑定已有账号入口均通过浏览器检查。
- 模拟器中文／英文确认页、确认／取消结果、过期提示、密码登录页与空表单禁用均已验证并留图。当前开发工具的旧自动化 SDK 元素查询会等待无返回，改由 WXML 已绑定处理函数执行状态测试并核对模拟器截图；这不是手机真实点击验收。
- 开发工具模拟器启动时出现绘制问题，使用其官方 CLI 的 `--disable-gpu` 重启后恢复；没有改变网站或用户系统的动画设置。

## 当前联调状态

Studio **20260910184755-studio-v7** 已部署，366 个文件哈希通过；源代码提交 `e024ae8`。归档 SHA-256：`c728f6055cff4f602526d12f52b61be4857ea980b0f861992c7ef27d10902193`。

服务端目前 `STUDIO_MINIAPP_ENABLED=1`、`STUDIO_MINIAPP_ENV=trial`、`STUDIO_WECHAT_PROVIDER=authing`。线上真实微信凭证交换与自有二维码生成均返回 200，公开默认仍是 Authing。凭据经私有环境文件写入，原环境文件已做 0600 备份。

首次部署后业务表与发布前备份逐表哈希一致；生成器发布目录、Server 酱启用状态／配额／密钥文件均保持。该次部署检查只建立短期扫码会话。后续店主亲自在手机进行账号操作和扫码确认，已验证真实网站登录；没有代店主合并账户、创建测试预约或修改账本余额。

店主已在微信后台保存 request、uploadFile、downloadFile 的 `https://pindoupuppy.com`。重新启动开发者工具并保持 `urlCheck=true` 后，真实 request 返回 200，原生登录页成功取得手机身份验证会话；公开品牌图片 downloadFile 返回 200。上传域名探针向只读 health 地址发送同一公开图标，收到预期的 405，证明请求已到服务器；没有生成订单、照片记录或业务账户。

**真机扫码登录已通过。** 店主两次扫描网站生成的 `develop` 小程序码，均在微信打开页面之前立即提示过期，网站没有收到 `/scan`；开发者工具直出的预览码则能打开。店主在后台设为体验版后，服务端切到 `trial`，校验码 7369 的网站二维码成功进入自有小狗授权页，店主确认完成操作。实际网站状态依次为 `qr_pending → qr_scanned → ready`，随后自动领取登录结果，页面显示账户、积分及退出登录入口。未放宽五分钟过期、原浏览器绑定或一次性领取保护。

本次已登录账号的只读核对结果为：自有小程序已绑定、旧 Authing 微信未绑定、邮箱为空。它目前是独立的微信账号；已询问店主仅用于测试还是要关联指定原邮箱账号，未执行身份重绑或账户合并。另已请店主确认后台当前体验版为新上传的 0.1.1，以保证通用体验码使用修正后的入口。

### 0.1.1 默认入口与旧云配置修复

店主发现通用体验码仍指向 `pages/index/index`。0.1.1 将默认页面改为 `pages/auth/studio-login`；原生端旧首页路径兼容跳转到新入口，原图纸前端的 H5 首页源代码保留。授权完成后的“回到小程序首页”也进入同一小狗页面。开发者工具清理编译缓存后，默认启动和旧路径跳转均在真实运行时验证为新账号页。

同时发现旧 `.env` 的 `VITE_API_BASE_URL` 仍覆盖 0.1.0 图纸接口，指向 CloudBase 的旧 HTTP 域名，尽管 `wx.cloud.callContainer` 已关闭。0.1.1 限定正式原生包使用 `https://pindoupuppy.com/api/v1`，正式 H5 使用同源 `/api/v1`；自定义环境和存储覆盖只在开发模式生效。实际运行时已验证 `BASE_URL=https://pindoupuppy.com/api/v1`、`USE_WX_CLOUD=false`。

服务器只读核验：项目登记的上海移动云 8 核源站上，`pindou`、`pindou-studio`、`nginx`、`cloudflared` 都处于 active，两个服务健康检查及网站公网健康检查返回 200。旧 CloudBase 域名 `/health` 返回 404 / `INVALID_HOST`，因此不能作为可用的免费后端继续依赖；这不能证明其控制台资源已删除或没有计费，未读取其账单。

证据位于工作区忽略目录 `artifacts/miniapp-login/`：`account-check.json`、`wx-code-exchange.json`、`qr-api-check.json`、`live-probes.json`、`upload-info.json`、`upload-0.1.1-info.json`、`backend-tests-fresh.txt`、`web-checks.json`、`native-checks.json`、`domain-validation.json`、`file-domain-validation.json`、`runtime-audit.json`、`runtime-0.1.1.json`、`trial-config.json`、`phone-trial-success.json`、`preservation.json` 及原生截图。凭据、原始登录 code、openid、session_key 与浏览器扫码令牌不写入这些报告。

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
