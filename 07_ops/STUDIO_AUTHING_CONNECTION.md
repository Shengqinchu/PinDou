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
| 当前登录回调 | `https://console.authing.cn/console/get-started/6aa0be1ff986e3e847b44a28` |

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

实际浏览器打开认证地址，HTTP200、标题pindoupuppy，登录页显示手机号／邮箱验证码输入框；尚未显示微信入口。没有发送短信、邮箱验证码、创建顾客账号或测试真实扫码。

下一步在Authing中创建“身份源管理→社会化身份源→微信→PC小程序扫码”，使用托管“小登录”，并关联到本App ID。平台自己的体验页先确认能扫码；普通“PC微信扫码”与托管小程序扫码不能混用。

当前仍保留平台体验回调。网站的正式回调、state/nonce/PKCE、服务端令牌验证、共享账号绑定及预约草稿返回尚待实现和验收，不能把首页填成未实现的回调地址。手机同屏扫码和免费版实际权限也尚未确认。

证据：忽略目录 `artifacts/authing-setup/openid-configuration.json`、`connection-check.json`、`hosted-login.png`。Git与截图未包含Secret或会话令牌。

逐步操作见[账号设置指南](STUDIO_AUTH_ACCOUNT_SETUP.md)。
