# Authing 应用配置记录

来源：店主2026-09-08 Toronto提供完整应用参数和截图，并授权明文保存。公开配置进入此文档；App Secret 按原值保存在项目本地 `.env`，供后续服务端调用。该文件已确认被Git忽略，本页不复制凭据。

## 当前应用

| 项目 | 已确认值 |
|---|---|
| 用户池名称 | PinDou Puppy |
| 用户池ID | `6aa0be1efd3e22731fd8727a` |
| 应用名称 | pindoupuppy |
| App ID | `6aa0be1ff986e3e847b44a28` |
| 应用类型 | 标准Web应用 |
| 域名模式 | 用户池内应用共用统一域名 |
| 认证地址 | `https://pindoupuppy.authing.cn/6aa0be1ff986e3e847b44a28` |
| Issuer | `https://pindoupuppy.authing.cn/6aa0be1ff986e3e847b44a28/oidc` |
| 当前登录回调 | `https://pindoupuppy.com/studio-api/auth/wechat/callback`、对应 www 地址；另保留原控制台体验地址 |

本地配置键：`STUDIO_AUTHING_APP_ID`、`STUDIO_AUTHING_ISSUER`、`STUDIO_AUTHING_APP_SECRET`。服务端正式接入时读取配置，不把Secret编入Vue资源。

## 端点核验

已读取该应用的[服务发现地址](https://pindoupuppy.authing.cn/6aa0be1ff986e3e847b44a28/oidc/.well-known/openid-configuration)，与店主提供参数逐项比对。以下路径均接在上表Issuer后：

| 功能 | 相对Issuer的路径 |
|---|---|
| 服务发现 | `/.well-known/openid-configuration` |
| JWKS公钥 | `/.well-known/jwks.json` |
| 认证端点 | `/auth` |
| Token端点 | `/token` |
| 用户信息 | `/me` |
| 登出 | `/session/end` |

发现文档支持authorization code、PKCE S256、`client_secret_post`及`client_secret_basic`。这证明公开配置一致，不等于已使用Secret完成真实授权换码。

## 当前可用性及下一步

最初实际浏览器打开认证地址时，HTTP200、标题pindoupuppy，只有手机号／邮箱验证码输入框。后续已直接通过店主的Codex内置浏览器完成如下配置：

| 项目 | 当前值 |
|---|---|
| 身份源标识 | `pindou-wechat` |
| 显示名称 | 微信登录 |
| 身份源ID | `6aa0ce3a0b1e3ba7a93c4c8c` |
| 连接ID | `6aa0ce3aa3e6038690d9a5de` |
| 类型 | `wechat:miniprogram:qrconnect` |
| 小程序 | Authing默认托管、正式版、非私有化 |
| 登录模式 | 可用于登录注册 |
| 自动账号绑定 | 关闭 |
| 关联应用 | pindoupuppy，已开启 |
| Authing默认登录方式 | 扫码登录；用于当前PC微信接入准备 |
| 当前方案 | B2C免费版；0/8,000活跃用户；有效期无限期；无支付方式 |

新的托管登录会话已生成二维码，显示“使用微信扫码登录”。体验页与控制台标签保留供店主验证。没有发送短信、邮箱验证码、代替店主扫码、创建顾客账号或开通付费套餐。手机网站不直接使用这张电脑扫码页，详见 `../02_product/STUDIO_MOBILE_AUTH.md`。

实际DOM确认二维码图片加载完成，原始尺寸430×430。局部“刷新”曾停在加载状态，重新从认证地址发起会话后恢复；Authing托管页日志出现过`Error: redirect`，尚未确定其内部原因。后续真实扫码及回调验收须覆盖二维码过期与重试，不能只凭图片加载成功开放网站入口。

2026-09-09 V6：网站正式回调、state/nonce/PKCE、签名验证、共享邮箱账户绑定与原路径返回已实现并发布。Authing 应用回调清单已保存主域名／www 的正式回调，保留原体验地址；身份源可选Callback仍留空。控制台确认 authorization_code、code、HS256、client_secret_post，与服务实现一致。

首次真实扫码，店主 iPhone 截图提示“无权限登录此应用”。随即核实应用“访问授权”默认行为确为“所有人 → 拒绝”。已按面向顾客公开登录的要求将此应用规则改为“允许”，二次读取确认已生效。这是Authing顾客认证应用访问权限，不改变网站管理员授权。重新生成会话后继续本人扫码验收；不能把本次错误写成网站已完成真实登录。

证据：忽略目录 `artifacts/authing-setup/openid-configuration.json`、`connection-check.json`、`hosted-login.png`。Git与截图未包含Secret或会话令牌。

逐步操作见[账号设置指南](STUDIO_AUTH_ACCOUNT_SETUP.md)。
