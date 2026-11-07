# PinDou 当前生产部署与运维

更新：2026-11-07。生产已完整迁移至 **36.139.201.94**（移动云华东-上海1，8核 / 16GB / 80GB / 8Mbps），到期 **2027-09-18**。网站、小程序后端、店主后台及原图纸服务均使用新机。2026-11-07 服务器加固（fail2ban、入站防火墙、自动安全更新）、每日备份、小程序通知改为正式版，见 [记录](SERVER_HARDENING_BACKUP_20261107.md)；生成器后端 current 为 `/opt/pindou/releases/20261107101920-pattern-threads`（图纸生成移出事件循环，回退 `20261017142309-timecard-offsale`）。当前 Studio release 为 `20261021235529-studio-v7`（轮播顺序与环境图精简为 12 张），此前为 `20261021224733-studio-v7`（首页 16 图轮播、详情页拼豆铺环境、座位文案与流程合并，见 `05_studio/DEVLOG.md` 2026-10-21），此前为 `20261017155424-studio-v7`（小程序编辑器与小店文案默认值，见 [记录](STUDIO_MINIAPP_0133_EDITOR_SHOP_20261017.md)），再之前为 `20261017151056-studio-v7`（图纸工具文案，见 [记录](STUDIO_MINIAPP_0132_PATTERN_TOOL_20261017.md)），再之前为 `20261017142359-studio-v7`；生成器后端 current 为 `/opt/pindou/releases/20261017142309-timecard-offsale`（时间卡暂时下架，见 `05_studio/DEVLOG.md` 2026-10-17；回退目标 `20261017141108-generator-free`），此前 Studio 为 `20261017141223-studio-v7`（普通生成免费），再之前为 `20261015005545-studio-v7`；预约时间页与结果页文案调整见 `05_studio/DEVLOG.md` 2026-10-14，此前为 `20261008015744-studio-v7`；储值优惠标题动效见 [记录](STUDIO_DEFAULT_ZH_AND_OFFER_CARD_RELEASE_20261007.md)，此前为 `20261008015320-studio-v7`；储值优惠标题同格式见 [记录](STUDIO_DEFAULT_ZH_AND_OFFER_CARD_RELEASE_20261007.md)，此前为 `20261008010730-studio-v7`；活动卡片二次调整见 [记录](STUDIO_DEFAULT_ZH_AND_OFFER_CARD_RELEASE_20261007.md)，此前为 `20261008005121-studio-v7`；默认中文与活动卡片醒目化见 [记录](STUDIO_DEFAULT_ZH_AND_OFFER_CARD_RELEASE_20261007.md)，此前为 `20261008003849-studio-v7`；预约页期中特惠见 [记录](STUDIO_MIDTERM_OFFER_RELEASE_20261007.md)，此前为 `20260929143831-studio-v7`；日记列表封面、标题摘要和阅读入口对齐及保全核验见 [发布记录](STUDIO_JOURNAL_LAYOUT_RELEASE_20260929.md)，此前剩余名额版本为 `20260929131938-studio-v7`；布贴剩余赠送名额独立编辑和保全核验见 [发布记录](STUDIO_PATCH_REMAINING_RELEASE_20260929.md)，此前积分版本为 `20260929000412-studio-v7`；布贴到店积分说明和服务端不可抵扣限制见 [发布记录](STUDIO_PATCH_POINTS_20260928.md)，此前布贴活动版本为 `20260928214037-studio-v7`；布贴试营业弹窗、动态名额与后台按人数赠送见 [发布记录](STUDIO_PATCH_LAUNCH_RELEASE_20260928.md)，此前预约布局为 `20260928210145-studio-v7`；预约布局、粉色容量提示和 9 月 30 日延长营业见 [发布记录](STUDIO_BOOKING_LAYOUT_RELEASE_20260928.md)，此前布贴预约为 `20260928200242-studio-v7`；布贴 DIY 独立一小时预约及样式核验见 [发布记录](STUDIO_PATCH_BOOKING_RELEASE_20260928.md)，此前后台保存反馈为 `20260927015327-studio-v7`；后台保存反馈全局修正与服务器健康检查见 [记录](STUDIO_ADMIN_FEEDBACK_AND_HEALTH_20260927.md)，此前商品保存提示为 `20260927013848-studio-v7`；新增商品保存提示修正见 [验收](STUDIO_SHOP_SAVE_FEEDBACK_RELEASE_20260926.md)，此前默认英文为 `20260926001311-studio-v7`；默认英文与小店默认拼豆套装见 [验收](STUDIO_DEFAULT_EN_SHOP_RELEASE_20260925.md)，此前英文品牌名统一为 `20260924180611-studio-v7`；英文品牌名统一见 [验收](STUDIO_BRAND_NAME_RELEASE_20260924.md)，商品图片上传提速见 [验收](STUDIO_IMAGE_UPLOAD_SPEED_20260924.md)，原分片上传修复见 [记录](STUDIO_IMAGE_UPLOAD_RELEASE_20260924.md)，顾客消息只读与商品图片切换见 [验收](STUDIO_MESSAGES_GALLERY_RELEASE_20260924.md)，顾客英文提醒修正见 [验收](STUDIO_NOTIFICATION_ENGLISH_CORRECTION_20260924.md)，订单与账户六图修正见 [验收](STUDIO_ORDER_ACCOUNT_UI_RELEASE_20260923.md)，此前订单与账号功能见 [记录](STUDIO_ORDERS_ACCOUNT_20260923.md)，店铺下单与补充装定价见 [记录](STUDIO_SHOP_CHECKOUT_20260923.md)。详见 [服务器资产与密钥位置](SERVER_ASSETS.md) 和 [迁移验收](PINDOU_FULL_MIGRATION_ACCEPTANCE_20260918.md)。

## 连接与目标确认

店主回国通道于 2026-09-29 扩展支持大冲锋 TCP 端口：专用 `cnproxy` 账户的 `PermitOpen` 改为 `any`，保留内网隔离、5 Mbit/s 限速和原运维账户配置。服务器与本机验收、限制和回退见 [游戏线路配置记录](CNPROXY_GAME_CONFIGURATION_20260929.md)。本次没有业务发布或数据库变更。

本机 `.env`（不进入 Git）中的部署入口：

```dotenv
PINDOU_PROD_SSH_HOST=36.139.201.94
PINDOU_PROD_SSH_USER=pindou
PINDOU_PROD_SSH_KEY_PATH=C:/Users/123/.ssh/pindou_mobilecloud_20260918_ed25519
```

常规运维使用 `ssh pindou-prod`，原有需要 root 权限的部署脚本使用 `ssh pindou-prod-root` 对应的同一新机和新 key。两个别名位于本机 `C:/Users/123/.ssh/config`。登录前先核对 `ssh -G pindou-prod` 中的 hostname、user、identityfile，登录后核对主机名 `19558948263` 和资产表中的主机指纹。

新电脑先安全取得已授权私钥、配置 key 路径，并核对服务器指纹；不可从 GitHub 获取私钥。原 `pindou_prod_ed25519` 是旧机 key，不再作为默认部署凭据。

## 当前运行结构

```text
网站 / 微信小程序
  -> Cloudflare 远程管理 Tunnel (pindou-staging)
  -> 新机 Nginx (https://localhost)
      -> pindou-studio.service / 127.0.0.1:8011
      -> pindou.service        / 127.0.0.1:8000
      -> 已发布的静态文件、图片和历史资源
```

| 服务 | current / 工作目录 | 环境与数据 |
|---|---|---|
| 原图纸与账号 `pindou.service` | `/opt/pindou/current/06_backend` | `/opt/pindou/shared/.env`；`shared/var/pindou.db`；`shared/data` |
| 店铺 `pindou-studio.service` | `/opt/pindou/studio/current/service` | `/opt/pindou/studio/shared/.env`；`shared/studio.sqlite3`；`shared/media` |
| Nginx / cloudflared | 当前生效的 systemd 配置 | 正式远端 Tunnel ingress 为准；旧本地 YAML 不代表线上入口 |

- 对外主域 `https://pindoupuppy.com`，同时保留 `www.pindoupuppy.com`、`staging.pindoupuppy.com`。Cloudflare 回源 `https://localhost`，`noTLSVerify=true`。域名和二维码不变。
- `pindou` 与 `pindou-studio` 是两套运行环境：Python 3.11.0rc1 / 3.10.12。生成器 venv/启动脚本依赖旧 release 路径，不能清理历史目录后再期待 current 正常启动。
- 当前数据是 **两个 SQLite 库 + 本地文件**。微信云托管 / MySQL / COS 是历史规划，不能因旧文档自动切换。
- 跨库身份使用生成器 `users.openid`；保留预约来源、账本、通知结果和幂等状态。
- 新机出站 IPv4 优先规则位于 `/etc/gai.conf`。它解决了不可达 IPv6 导致邮件/图纸连接等待的问题；不要只照抄一个 precedence 条目而丢掉其余默认优先级。

## 只读检查

在已连接的新机执行，避免输出完整环境文件或带 token 的进程参数：

```bash
hostname
systemctl is-active pindou.service pindou-studio.service nginx.service cloudflared.service
systemctl is-enabled pindou.service pindou-studio.service nginx.service cloudflared.service
readlink -f /opt/pindou/current
readlink -f /opt/pindou/studio/current
df -h /
curl --fail --silent http://127.0.0.1:8000/health
```

公网用主域检查首页、店铺、预约接口及 `/health`；出现异常时区分进程就绪、源站路由与 Cloudflare 缓存。发布后以日志中的本次请求标记确认流量确实到达新机。

## 后续发布

1. 按本次任务明确的产品范围准备提交，保留其他工作区改动。迁移不能被用作发布本地未验收功能的理由。
2. 确认 `.env` 和本次连接目标为新机，读取实际 current 版本，再准备可回退的 release、文件清单与一致性数据备份。
3. Studio 现有工具为 `studio_pack.py`、`studio_upload.py`、`studio_release_audit.py`、`studio_deploy.py`。上传工具只传包，不等于部署；后两项会涉及正式数据/服务，先读脚本再执行。上传/审计脚本当前以 root 读取 `.env` 中的新 host / key。
4. 使用 release + current 符号链接流程。需要停写或改 schema 时，同时考虑两个库、通知 workers 和 Mac 短信桥，不让它们跨不一致的快照继续写入。
5. 校验发布文件、受保护表、余额/流水、身份关联和服务就绪，再做受影响的公网功能检查。只报告实际验证过的层级。

私钥、密码、应用环境文件及完整客户备份保持在授权的本机/服务器目录。模板 `.env.example` 只提供非秘密字段。

账号登录／微信重复号的受控恢复使用 [2026-09-29 恢复规则与发布记录](STUDIO_ACCOUNT_RECOVERY_20260929.md) 和 `studio_account_recovery.py`。先只读预检；恢复前双库备份，保留稳定顾客 ID 和账本，不按注册时间或填写的联系号批量合并。

## 备份与旧机

2026-11-07 起每天 03:30（Toronto）自动备份两库、两个 shared 目录与服务配置到 `/var/backups/pindou`，保留 14 天加 6 个月的月份，失败经 Server酱 通知店主；内容、离机副本与恢复步骤见 [加固与备份记录](SERVER_HARDENING_BACKUP_20261107.md)。发布前的一致性数据备份仍按上文执行，不能用夜间备份代替。

迁移备份在新机 `/root/pindou-migration-20260918` 及本机 `D:/Users/123/Documents/PinDouBackups/20260918`，校验索引为 `MIGRATION_BACKUP_INDEX.json`。整根归档、最终数据库/文件和系统增量已验证恢复；它只覆盖 2026-09-18 切换时点。

旧机 `36.137.177.135` 的业务应用与正式 Tunnel 已停止并禁用，仅保留回退资料。其用户提供到期时间为上海时间 2026-09-25 22:41:52。新机开始写入后，回退必须冻结新机并反向同步全部最新状态，详见 [验收中的回退流程](PINDOU_FULL_MIGRATION_ACCEPTANCE_20260918.md#回退与交接)。同一时刻只运行一个正式 Tunnel 和一组通知消费者。

## 历史参考

- [原服务器部署记录](deployment_legacy.md)：旧机配置、旧到期日和阶段性实施记录。
- [微信云托管方案与迁移前文档快照](deployment_cloudrun_reference.md)：历史路径，不是当前生产步骤。
- [完整迁移手册](PINDOU_FULL_MIGRATION_RUNBOOK_20260918.md)、[执行记录](PINDOU_FULL_MIGRATION_EXECUTION_20260918.md)。
