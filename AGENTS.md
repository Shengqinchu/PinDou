# PinDou 运维入口

- 当前生产目标是 **36.139.201.94**（移动云上海1），2026-09-18 已完成迁移；到期日 **2027-09-18**。先读 [服务器资产](07_ops/SERVER_ASSETS.md) 和 [部署说明](07_ops/deployment.md)。
- 当前 Studio 业务开发/运维分支是 `codex/studio-v1-20260907`；GitHub 默认 `phase2` 保留旧生成器代码，不等于实际线上最新版本。部署前核对分支和生产 current，不能只凭默认分支重新打包上线。
- 本机部署读取根目录 `.env` 的 `PINDOU_PROD_SSH_HOST` / `PINDOU_PROD_SSH_USER` / `PINDOU_PROD_SSH_KEY_PATH`；常规登录使用 `ssh pindou-prod`，需要 root 时使用 `ssh pindou-prod-root`。操作前确认目标，不从历史报告抄旧 IP。
- `36.137.177.135` 已停止业务，仅保留回退资料。正式 Tunnel、应用写入者及通知消费者只能运行一组。回退前必须恢复新机最新状态，不能直接启动旧快照。
- 生产包含 `pindou.service` 和 `pindou-studio.service` 两个应用及两个 SQLite 库；完整备份/迁移同时覆盖身份、预约、余额、通知队列、图片和历史依赖。
- 私钥、密码、生产环境文件、顾客记录和完整备份不提交 GitHub；文档记录位置与公钥指纹。
- 保留其他任务的工作区改动。按任务范围提交，不能把本地未验收产品代码随运维修改部署。
- 服务器、key 或续费变化同步 [资产记录](07_ops/SERVER_ASSETS.md)、部署文档和共享 `apisell/服务器资产清单.md`；重要变更记入 `05_studio/DEVLOG.md`。历史时间点不作为当前状态。
- `05_studio` 目录继续遵守其自身的 `AGENTS.md`。
