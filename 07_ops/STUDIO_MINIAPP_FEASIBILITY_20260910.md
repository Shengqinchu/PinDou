# 自有微信小程序可行性验证

> 后续实施更新：自有品牌原生授权已完成开发，修正版 **0.1.1** 已上传，三类合法域名已验证；切换体验版后，店主已完成手机扫码确认，网站实际完成登录。尚未正式发布。实际状态以 [自有小程序扫码实施记录](STUDIO_MINIAPP_LOGIN.md) 为准，下文保留此前只做可行性调查时的证据。

本记录对应 2026-09-10 的预约通知与沟通调研。结论是：已有 uni-app 工程可以编译，尚不能作为正式的自有网站扫码登录版本发布。完整建议见 [调研报告](../01_research/tech/STUDIO_MESSAGING_RESEARCH_20260910.md)。

本轮只做本地代码核查和隔离构建，没有上传、提审、发布小程序，没有发送 bot 消息，也没有改变现有网站登录或业务数据。

## 证据范围

- 用户最新两张微信后台截图：小程序“双吉拼豆图纸定制”，基础资料、类目、开发者和备案已完成；微信认证未完成；开发、审核、线上版本均为空。
- 用户回复：不确定主体类型。
- 本地源代码检查基于主仓库 HEAD 2227adc 和当前工作区。05_web、06_backend 中既有未提交修改保留，未纳入本轮研究文档变更。
- 编译器与终端的真实返回，不将其替代微信开发者工具或 iPhone/Android 真机测试。

## 构建

工作目录：

~~~text
C:\Users\123\Desktop\PinDou\05_frontend
~~~

PowerShell 中执行：

~~~powershell
$env:UNI_OUTPUT_DIR = 'C:\Users\123\Desktop\PinDou\artifacts\miniapp-feasibility\build'
npm.cmd run build:mp-weixin
~~~

本机 Node v24.19.0、npm 11.17.0；使用已有 node_modules，没有重新安装或升级依赖。终端报告 Compiler version: 5.11（vue3），退出码 0，并输出 Build complete。出现 Sass legacy-js-api 弃用提示及插件耗时提示，没有编译失败。

隔离产物共 **84 个文件，919,229 bytes**，没有进入生产发布目录。关键文件：

| 文件 | SHA-256 |
|---|---|
| app.json | 5e6a45764a5d5f88d45fbd3dea6797d49152eacfa006185a123a1ce37f4cdc26 |
| project.config.json | 3a9607f24a6c557595dbf5a3f5e23555949fab8dd7259e742d988ba4d7942ac9 |

## 配置与功能差距

| 检查项 | 观察 | 后续动作 |
|---|---|---|
| src/manifest.json | AppID wx9f2b4d171e92a5ef | 与微信后台应用对应再做发布校验 |
| 根 project.config.json | 仍为旧 AppID wx487ee622705c95ec | 统一开发工具配置，避免导入错误工程 |
| 构建 project.config.json | AppID wx9f2b4d171e92a5ef | 本次构建没有沿用旧尾号 95ec |
| 合法域名检查 | 构建配置 urlCheck 为 false | 真机验收必须启用检查并配置实际合法域名 |
| src/pages.json | 已有图纸工具页面；没有网站扫码确认/结果专用页 | 补齐原生授权产品流程 |
| src/utils/request.ts | 小程序使用 uni.login，向 /user/login 提交 code | 接口必须真正校验微信身份 |
| 06_backend/pindou/api/user.py /login | 早期代码把 code 哈希为 openid；未做微信服务端身份交换 | 该开发占位实现不能承载正式自有登录 |
| Studio 当前微信入口 | 独立的 Authing QR/身份验证代码 | 保持现有方式；新身份源经测试后再迁移 |

上述 /login 结论仅针对检查到的本地旧小程序对应代码，不能当作生产 Studio Authing 登录链路的故障证据。

## 发布前仍需完成的验证

1. 确认主体、类目、开发者权限，以及本次要使用的微信 API/合法域名权限。
2. 若走 Authing 私有小程序，确认其源码/权益，并实际取得适用版本；若走自研，则实现真正的微信登录与扫码会话。
3. 扫码会话具备短有效期、单次确认/领取、原浏览器绑定、过期和拒绝流程，客户端传来的账号 ID 不作身份依据。
4. 新旧身份源通过稳定内部账号关联；已有积分、时长、图纸、预约与个人资料保持同一个所有者，不按昵称或邮箱静默合并。
5. 微信开发者工具与真机分别验证：扫码、取消、过期、重复确认、错浏览器领取、语言、网络失败，以及微信内/普通手机浏览器同机流程。
6. 上传体验版、审核和发布结果分别记录。当前截图明确没有上传版本，因此不能标记任何一项已完成。

Authing 官方依据：[微信 PC 小程序扫码](https://docs.authing.cn/v2/guides/connections/social/wechat-miniprogram-qrconnect/)。其私有小程序说明确认了可以定制品牌，但未证明当前账号已拥有源码或相应套餐权益。
