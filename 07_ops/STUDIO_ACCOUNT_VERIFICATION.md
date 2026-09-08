# 共用账号与预约登录发布记录 · 2026-09-08

代码提交：`b7ada69`；分支：`codex/studio-v1-20260907`。产品范围与未开通渠道见 `02_product/STUDIO_ACCOUNT_PLAN.md`；免费额度和微信接入条件见 `02_product/STUDIO_LOGIN_CHANNEL_RESEARCH.md`。

## 上线行为

- 首页、日记、详情、价格和预约时间表公开。最终提交预约需要已验证邮箱账号；登录后继续同一份表单，取消／错误保留选择。
- 复用图纸工具的邮箱验证码、邮箱密码及注册接口、用户 ID、JWT。`pd_web_token` 和 `pd_web_user` 与原工具相同；同源浏览器可沿用，新设备用同账号登录。浏览器本地存储受限时，当前页面可保留内存登录状态。
- Studio 只向固定 loopback 账号服务转发允许的接口，禁止上游重定向；不接入原开发版微信身份占位。密码、验证码和 JWT 不写入服务器访问日志或发布文档。
- `studio_reservations.owner_id` 为新增列，新预约由服务端绑定已认证的账号，按账号查询／重试。其他账号不允许读取或重放；历史匿名回执保持原浏览器权限，不按姓名、联系方式猜测归属。
- 新增我的预约（最近 50 条）、退出登录和可选密码设置。账号抽屉按需加载约 5.19 KB gzip；中文正文字体补齐新增登录文案需要的 13 个汉字。
- 微信和手机号选项尚未启用：微信缺官方账号及授权配置；手机号本轮仅调研，没有开通计费或发送短信。

## 验证与证据

- 后端全套 **82 项通过**；最后错误映射的小调整后，账号专项 **11 项再次通过**。
- 浏览器 **38 组检查通过**，覆盖中英文、Chromium 320／390／768／1440、WebKit 390、微信 Android／iOS 模拟、旋转／缩小视口、取消保留草稿、错误验证码、一次登录继续一次提交、账号共享、退出后需再登录、可选密码注册与错误密码。
- `npm run build`：52 个文案模块锁定检查、TypeScript、Vite 均通过。
- 源站用现有账号的短期内部验证令牌，实际检查原账号服务与 Studio `/auth/me` 的用户 ID 一致，且本人预约接口返回 200；不输出用户资料或令牌，不创建用户／预约。
- 源站匿名预约请求返回 401，账户查询 401，非法邮箱参数 422，公开时间表／日记 200。预约表记录数在拒绝检查前后不变。
- 公网普通 URL 的中文／英文桌面及 WebKit 手机页面均加载新 build，登录弹窗可用、价格保持 CAD、无横向溢出；额外检查 WebKit 从菜单进入预约页后仍可打开登录。
- WebKit 公网检查记录到 Cloudflare `cdn-cgi/rum` 统计上报的访问控制警告，调用栈来自 Cloudflare beacon；与站点错误分开保留在 JSON 中，业务导航／登录／时间表检查通过，没有修改或关闭统计设置。
- 本轮没有向真实客户邮箱发送测试验证码，未创建生产测试预约；邮箱流程由本地账号服务替身验证，线上验证到原账号鉴权链路。微信浏览器检查是模拟，不是真机微信 OAuth 测试。

本地证据：`artifacts/studio-account/browser-verification.json`、`origin-verification.json`、`live-verification.json`、截图和 `deploy-result.json`。

## 发布与回滚

- 发布：`20260908224009-studio-v3`，268 个文件逐一校验通过。
- Build：`2026-09-08T22:38:56.535Z`；入口 `index-BXUCsDiC.js`；账号组件 `AccountPanel-CC2feaU4.js`。
- 归档 SHA-256：`3f48e5cdaeb5087fd8e47010e801cd7c6069e3dd9387df1191574a16c91c3611`。
- 当前：`/opt/pindou/studio/releases/20260908224009-studio-v3`。
- 回滚备份：`/opt/pindou/studio/backups/20260908224009-studio-v3`。
- 新数据库列与限流表为增量迁移；发布未修改经营配置、价格、现有内容覆盖或原工具源文件。包中确认排除 `qa_server.py`、`auth_fixture.py`、测试文件与凭证。
- 原生成器首页 SHA-256 保持 `506f9bd2f9f0c37c52f08924f1504286816b93bff3198aea9f1790d0eceb36aa`；`pindou` / `pindou-studio` 均 active，Nginx 检查通过，Studio health 为 ok。
