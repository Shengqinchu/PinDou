# 小狗拼豆铺 Studio V1 运维

## 独立入口

- 网站预览：`https://pindoupuppy.com/studio/`
- 预约：`/studio/visit`
- 选购与自提询单：`/studio/shop`
- 工作室日记：`/studio/journal`
- 店主工作台：`/studio/manage`，使用现有拼豆后台管理员账号。
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

## 预约和询单

每份请求保存顾客主动填写的称呼、联系途径、联系信息、备注，以及日期人数 / 选购清单。提交结果为 pending。不是已付订单，不锁定座位或库存。

管理员读取和更新都通过旧后台核实签名令牌，然后要求完整 admin 角色。这里没有新增管理员密码，没有复制旧服务密钥。内部备注不向公众开放；更新使用版本号防覆盖，并保存状态审计记录。

店主必须主动打开工作台处理意向，使用顾客填写的联系方式确认。当前没有邮件、短信、微信自动推送，也没有在线付款。

## 本地运行

前端：在 `05_studio` 执行 `npm install`、`npm run dev`，地址为 `http://127.0.0.1:5184/studio/`。
后端：在 `06_studio` 安装 requirements，设置 `STUDIO_DB_PATH` 后执行 `python -m uvicorn app:app --host 127.0.0.1 --port 8011`。
测试：`python -m pytest test_app.py -q`；前端 `node scripts/verify.mjs` 默认连接本地服务并创建明确的 QA 数据。正式域名验收设置 `STUDIO_SKIP_SUBMIT=1`，避免创建顾客请求。

开发机没有运行旧管理 API 时，本地管理员登录需要转发旧 `/api/v1/admin/login`；线上部署同源即可使用。

## 发布

1. `npm run build`，完成浏览器检查和后端测试。
2. 从项目根目录执行 `python 07_ops/studio_pack.py`。它只打包 `05_studio/dist` → `site/studio/` 以及 `06_studio/app.py`、`requirements.txt`、`requirements.lock.txt` → `service/`，建立每文件 SHA-256 manifest，再计算归档哈希。首次发布后补充了实际环境 lock；后续发布脚本优先使用 lock。
3. 使用 `.env` 的 SSH 配置连接，凭证不写入文档和包。2026-09-07 普通部署用户的密码老化策略阻断了非交互 SSH；既有 root key 可正常登录，本轮未修改任何账号 / 密码策略。
4. 上传包和 `07_ops/studio_deploy.py`，执行 `python3 studio_deploy.py <archive> <release> <sha256>`。脚本先校验、备份、启动新服务，再验证 Nginx 并 reload。不会重启 `pindou.service`。
5. 核对线上 HTML 哈希、图片和 API；核对旧首页 HTML 与旧健康检查。记录发版结果到 `STUDIO_VERIFICATION.md`。

## 回滚

优先恢复备份中的 Nginx 文件，并执行 `nginx -t`、`systemctl reload nginx`。这样旧站点会恢复原先全部规则。若仅退回工作室上一版本，恢复备份 `state.json` 记录的 `previous_current` 符号链接并重启 **pindou-studio**。

首次部署需完全下线工作室时，可以停止并禁用 `pindou-studio.service`。保留数据库、发布包和备份，以便恢复；不要删除顾客请求或原工具目录。

## 后续经营配置

需店主确认最终营业时间、接待人数、停车安排，以及真实商品 SKU / 款式 / 库存 / 加元价格 / 税费，再切正式商城交易。主网站切根路径另做路由调整，必须保留生成器旧链接。
