# 小狗拼豆铺 Studio V1 运维

## 当前 VISION 版本

当前路径与业务规则见仓库中的 02_product/STUDIO_VISION.md 和 STUDIO_VISION_VERIFICATION.md。到店页改为两周时间表与人工确认；结果为 /studio/reservation/:id，详情为 /studio/details。商城开发中，/cart 转向小店。下面交易部分保留历史与后续运维用途，当前不开放新购买。

新版独立表：studio_reservations、reservation_events、reservation_policy；结果依赖 HttpOnly/Secure 同浏览器会话。STUDIO_ONLINE_SALES 默认 0，暂停新报价/付款单，旧订单与回调继续保留。STUDIO_RESERVATION_COOKIE_SECURE 生产保持默认 1，只有 loopback QA 使用 0。新预约小时规则和两周窗口见 06_studio/reservations.py。发布包需包含新增的 reservations.py。

## 独立入口

- 网站预览：`https://pindoupuppy.com/studio/`
- 到店体验与真实时段：`/studio/visit`
- 商品选购：`/studio/shop`
- 购物车与结账：`/studio/cart`
- 付款／订单确认：`/studio/order/:id`
- 工作室日记：`/studio/journal`
- 店主工作台：`/studio/manage`，使用现有拼豆后台管理员账号。
- 工作台模块：今日概览、订单搜索与详情抽屉、七天日历／营业排班、商品编辑、收款设置、操作记录和历史询单；切换模块保留草稿。
- 独立 API：`/studio-api/`，独立健康检查：`/studio-api/health`。
- 旧工具保留 `/`、`/upload`、`/tutorial` 及现有 API；本轮没有修改旧前后端源文件，也没有迁移旧数据库。

## 服务结构

工作室使用原服务器和原 Cloudflare Tunnel。新增 Nginx 前缀规则，原站点规则保留。

| 项目 | 位置 |
| --- | --- |
| 独立发布目录 | `/opt/pindou/studio/releases/<release>/` |
| 当前工作室版本 | `/opt/pindou/studio/current` 符号链接 |
| 静态站 | `current/site/studio/` |
| FastAPI 服务 | `current/service/app.py` |
| 独立虚拟环境 | `/opt/pindou/studio/venv` |
| 独立数据库 | `/opt/pindou/studio/shared/studio.sqlite3` |
| systemd | `pindou-studio.service`，绑定 `127.0.0.1:8011` |
| 部署前备份 | `/opt/pindou/studio/backups/<release>/` |

独立数据库不进入 git，不放进静态目录。系统服务以 `pindou` 用户运行，数据目录权限 0700，文件 umask 0077。API 及 HTML 预览使用 no-store，构建资源带哈希缓存。

## 购物车、支付和排班

当前交易规则见 `02_product/STUDIO_COMMERCE_V1.md`。服务器核价，结账暂留座位与实物库存，虎皮椒付款经签名验证和主动查单后自动确认。订单数据仍只保存在独立 studio SQLite。旧预约和询单历史保留，不迁入已付订单。

管理员读取和更新都通过旧后台核实签名令牌，然后要求完整 admin 角色。这里没有新增管理员密码，没有复制旧服务密钥。内部备注不向公众开放；更新使用版本号防覆盖，并保存状态审计记录。

店主在工作台维护营业时间、人数、商品和库存；顾客从付款页即时看到确认。当前没有邮件、短信、微信自动推送。真实营业安排和税费方式尚待店主填写，初始不开售。

虎皮椒配置使用 `/opt/pindou/studio/shared/.env`，0600 权限。`studio_payment_setup.py --configure` 只从现有 PinDou 共享环境复制商户 ID／密钥／网关到这个独立文件，已存在则保留。旧生成器的回调 URL 不复制、不修改。Studio 回调固定 `/studio-api/payments/hupijiao/notify`，无须修改商户公共回调配置。

## 本地运行

前端：在 `05_studio` 执行 `npm install`、`npm run dev`，地址为 `http://127.0.0.1:5184/studio/`。
后端：在 `06_studio` 安装 requirements，设置 `STUDIO_DB_PATH` 后执行 `python -m uvicorn app:app --host 127.0.0.1 --port 8011`。
测试：`python -m pytest -q`；交易界面完整测试使用本地 `python qa_server.py` 加 `node scripts/verify-commerce.mjs`，数据库与网关均为隔离测试。此测试入口只绑定 loopback，不打包到服务器。旧 `verify.mjs` / `verify-refinement.mjs` 部分选择器对应历史询单页；当前交易验收使用 `verify-commerce.mjs`。

店主工作台与动效验收：`node scripts/verify-desk-motion.mjs`、`node scripts/verify-desk-resilience.mjs`，使用独立本地 QA 网关；前者包含测试数据写入，不能用于生产域名。生产只读检查使用 `verify-live.mjs` 和 `verify-commerce-live.mjs`。当前独立审查修正与发布记录见 `STUDIO_0830_VERIFICATION.md`；`STUDIO_MOTION_V2_VERIFICATION.md` 保留上一版历史。补充检查：`verify-responsive-motion.mjs` 覆盖多引擎与断点，`verify-webview-lifecycle.mjs` 覆盖键盘／安全区／横竖屏与收银台入口，`verify-list-continuity.mjs` 检查快速筛选时的卡片位置。0830 的具体复现与修正检查为 `verify-0830-fixes.mjs`、`verify-0830-layout.mjs`、`verify-0830-inputs.mjs`、`verify-0830-polish.mjs`；最后一项也可设置 `STUDIO_BROWSER=webkit` 检查 WebKit，均只用于本地 QA。

开发机没有运行旧管理 API 时，本地管理员登录需要转发旧 `/api/v1/admin/login`；线上部署同源即可使用。

## 发布

1. `npm run build`，完成浏览器检查和后端测试。
2. 从项目根目录执行 `python 07_ops/studio_pack.py`。它只打包 `05_studio/dist` → `site/studio/` 以及 `06_studio/app.py`、`commerce.py`、`payments.py`、`requirements.txt`、`requirements.lock.txt` → `service/`，建立每文件 SHA-256 manifest，再计算归档哈希。发布脚本使用固定依赖 lock，不打包测试服务器或凭证。
3. 使用 `.env` 的 SSH 配置连接，凭证不写入文档和包。2026-09-07 普通部署用户的密码老化策略阻断了非交互 SSH；既有 root key 可正常登录，本轮未修改任何账号 / 密码策略。
4. 上传包和 `07_ops/studio_deploy.py`，执行 `python3 studio_deploy.py <archive> <release> <sha256>`。脚本先校验、备份、启动新服务，再验证 Nginx 并 reload。不会重启 `pindou.service`。
5. 核对线上 HTML 哈希、图片和 API；核对旧首页 HTML 与旧健康检查。记录发版结果到 `STUDIO_VERIFICATION.md`。

## 回滚

优先恢复备份中的 Nginx 文件，并执行 `nginx -t`、`systemctl reload nginx`。这样旧站点会恢复原先全部规则。若仅退回工作室上一版本，恢复备份 `state.json` 记录的 `previous_current` 符号链接并重启 **pindou-studio**。

首次部署需完全下线工作室时，可以停止并禁用 `pindou-studio.service`。保留数据库、发布包和备份，以便恢复；不要删除顾客请求或原工具目录。

## 后续经营配置

固定汇率已由店主指定为 1 CAD = 5 CNY。需在工作台设置营业时间、接待人数及售价税费方式，再开启网上购买；实物填写价格、款式及库存后上架。主网站切根路径另做路由调整，保留生成器旧链接。
