# 英文 Logo、到访照片与登录准备验证 · 2026-09-08

店主本轮提供两张英文品牌 JPG，以及三张到访／停车原图。资料与来源：`03_design/STUDIO_ENGLISH_BRAND.md`、`03_design/STUDIO_ARRIVAL_PHOTOS.md`；登录调研和未完成的实际接入项见 `02_product/STUDIO_AUTH_PHASE1.md`。

## 本地检查

- 56 个文案模块检查、TypeScript、Vite 构建通过。授权源 `owner-20260908-english-logos-and-arrival-photos`。三个既有内容模块的变化限定为新图辅助名称、微信复制元数据和编辑器必要标签。
- Logo 26 组检查：Chromium 320–2560 宽、横屏和短笔电屏幕；WebKit 手机、平板和桌面；中英文均无横向溢出。英文原图显示在预期位置，中文原图不变。
- 指引图 24 组检查：两引擎／两语言，含 600/601px 布局切换。三张图片比例均为 1280/1707，全部原图可读；桌面并排、手机单列，三张均可打开／关闭原图查看器。
- 微信区域鼠标、键盘 Enter 与剪贴板拒绝后的手动复制均通过；44px 点击区域独立于主页链接，没有嵌套按钮。
- 视觉复查发现旧 `.copy-contact:hover` 的不透明背景遮挡原图文字，已在 `FooterBrand` 范围覆盖为透明，另为44px按钮留出底部空间，避免焦点环压到 rednote 行。
- 10 项短信配额准备测试、11 项现有邮箱账号回归、9 项内容服务测试通过。配额测试包括150个并发请求，使用独立SQLite；没有真实短信调用。
- 准备模块 `sms_policy.py` 未注册公共端点、未进入生产打包清单。手机号与微信选项仍为关闭，不声称真实账号接入已完成。

证据：`artifacts/english-brand-auth/local-layout.json`、`local-arrival.json`、原图和页头／页脚截图。开发预览为 loopback 测试环境，微信真机扫码不在本轮验证范围。

## 发布前状态

源站原发布 `20260909003439-studio-v4`。媒体草稿与发布版本均为3，只有店主的 `shop-collage` 上传覆盖；两套英文 Logo 和到访照片不存在店主覆盖，因此可以使用新 shipped defaults，不需要改写线上内容数据库。

旧生成器首页 SHA-256：`506f9bd2f9f0c37c52f08924f1504286816b93bff3198aea9f1790d0eceb36aa`。保存到 `artifacts/english-brand-auth/origin-before.json`，发版后再次核对。

## 发布结果

- 代码 `edc3844` 已推送到 `codex/studio-v1-20260907`。
- 发布：`20260909012942-studio-v4`；build `2026-09-09T01:27:03.374Z`；JS `index-BZ1HstiU.js`；CSS `index-CnAdAK3r.css`。
- 发布包 SHA-256：`0d9d2e5faff52d971c9f6d2f7d0765658f853af32b4250c90128b064959a99dc`，14 个上传分片和全部297个发布文件校验通过。
- 当前目录 `/opt/pindou/studio/releases/20260909012942-studio-v4`；备份 `/opt/pindou/studio/backups/20260909012942-studio-v4`。
- 普通域名 `https://pindoupuppy.com/` 返回上述 build，无需 version 查询参数；www 正确重定向到根主页。五张图片公网均200，逐字节 SHA-256 与附件一致。
- 公网重新执行 Logo 26 组、指引图24组检查，两引擎中英文均通过；图片查看器打开关闭、鼠标／键盘复制和手动复制回退通过，无页面运行异常。
- 源站 `pindou`／`pindou-studio` 均 active，Studio health 0.7.0；Nginx 配置校验通过。旧生成器首页哈希不变。
- 线上媒体草稿与发布内容／版本均与部署前一致，店主 shop-collage 覆盖保留。媒体编辑接口合并后有52项，包含新增英文页脚和三张指引图。
- `/studio-api/auth/options` 仍为 email/password true、wechat/phone false。短信准备模块未进入生产发布；没有重置账号或改动生成器身份库。

证据：`artifacts/english-brand-auth/deploy-result.json`、`origin-after.json`、`public-assets.json`、`live-layout.json`、`live-arrival.json`。本轮代码和验证记录均更新 GitHub。
