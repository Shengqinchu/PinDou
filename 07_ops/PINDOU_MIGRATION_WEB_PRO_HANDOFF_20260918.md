# PinDou 完整迁移：Web Pro 任务交接

> **已完成，历史交接归档**：后续由主任务完成迁移，2026-09-18 12:20:35 Toronto 公网验收通过。当前生产为 `36.139.201.94`，到期 **2027-09-18**；`.env` 已使用新机、新 key。继续运维请读 [服务器资产](SERVER_ASSETS.md) 和 [迁移验收](PINDOU_FULL_MIGRATION_ACCEPTANCE_20260918.md)。下文“未开始”等仅表示当时交接阶段，不是当前待执行任务。

状态更新：2026-09-18。用户已购买新机，明确要求配置 SSH key，并开始完整迁移；要求另开任务使用 **ChatGPT Web — Pro（chatgpt-web/pro）**，以节约模型用量。此前文档的“只读调查”是历史阶段，不能据此反复要求用户授权正常的迁移准备。

已创建执行任务：`01a0b4f0-6568-7a80-a86e-f7fb931f80f2`，名称“PinDou 完整迁移到新移动云服务器”；app-server 返回模型 `chatgpt-web/pro`，首轮 `01a0b4f0-98ee-7e33-8870-721653151ee9` 已开始。调度状态位于 `artifacts/migration-research-20260918/web-pro-task-state.json`，隐藏的一次性本机 runner PID 42668 负责保持该任务会话（不属于重复自动化）。

**首轮后续更新**：该轮已结束；新任务报告两次只读工具调用遭 OpenAI 工具安全检查拦截。当前迁移未启动，runner 完成首轮后退出，不会自动重试。详细状态见 `07_ops/PINDOU_FULL_MIGRATION_EXECUTION_20260918.md`。下次继续需恢复执行通道，不能将首轮完成误当作已备份/已同步。

## 已完成

- 源机全量迁移调查和执行手册已完成，先读下列文件，不要重新盘查所有聊天。
- 新机 `36.139.201.94`、root 密码登录成功，已生成并安装独立 Ed25519 公钥。
- 第二条独立连接以新密钥认证成功，authorized_keys 为 `600 root:root`；保留原密码登录方式，未改 sshd 配置。
- 新机实测 Ubuntu 22.04.5 x86_64、8 CPU、约 15.61 GiB RAM；根盘约 78.56 GiB，已用约 8.41 GiB，可用约 66.74 GiB。
- 用户截图显示移动云华东-上海1、8Mbps、内网 IPv4 192.168.0.41，实例到期 2027-09-18 21:23:25；截图事实与 live OS 事实分开记录。
- 尚未同步生产文件、开始正式应用、变更旧机、停写、切流量或发送通知。当前迁移只能由本新任务继续执行，原任务不并行操作生产。

## 工作区与入口

项目：`C:/Users/123/Desktop/PinDou`，分支 `codex/studio-v1-20260907`。存在大量其他任务的脏改动，保留它们；从实际线上 release 搬迁，不要把当前工作区重新打包发布。

| 项目 | 位置 |
|---|---|
| 调查报告 | `01_research/PINDOU_FULL_MIGRATION_ASSESSMENT_20260918.md` |
| 详细迁移/回退手册 | `07_ops/PINDOU_FULL_MIGRATION_RUNBOOK_20260918.md` |
| 源机 SSH 配置 | 项目根 `.env`：PINDOU_PROD_SSH_HOST / PINDOU_PROD_SSH_KEY_PATH；保留为旧生产，最终切换验收后再更新 |
| 源机 | `36.137.177.135`，root，`C:/Users/123/.ssh/pindou_prod_ed25519` |
| 新机 | `36.139.201.94`，root，`C:/Users/123/.ssh/pindou_mobilecloud_20260918_ed25519` |
| 新机密码私密记录 | `artifacts/migration-research-20260918/private/target-access.json`；用户要求落档，已完成，不用重复索取或警告 |
| 新机 SSH 主机指纹 | `SHA256:vpubF8HbgFW+ig0UIWRfS9f4nij1ge5H2RBL5t1ddz4`，首次连接记录，已写入本机 known_hosts |
| 新机实测证据 | `artifacts/migration-research-20260918/target-bootstrap.json` |
| 源机证据 | 同目录 source-inventory/detail/business/followup/schema.json 与只读 collector |
| 表基线 | `01_research/migration-evidence-20260918/DB_BASELINE_20260918.csv`，84 表，是 9/18 旧只读时点，最终冻结时重新生成 |

Windows 可用 `C:/Python313/python.exe -X utf8`、Paramiko、OpenSSH。使用已知主机指纹验证。不得打印密码、私钥或全 env；本地 private 目录已限制 ACL，并位于 Git 忽略的 artifacts 下。

## 关键事实，避免重新踩坑

1. 旧机到期基准：北京时间 **2026-09-25 22:41:52**，加东 **9/25 10:41:52**；当前账单变更仍未核实。时间充足可以今天开始预迁移，争取 9/22–23 前切换；不能等到最后一天。
2. 两个必须一起迁移的服务：pindou（8000，原图纸和账号）、pindou-studio（8011，小店）。两库均 SQLite：`/opt/pindou/shared/var/pindou.db`（17 表，delete）和 `/opt/pindou/studio/shared/studio.sqlite3`（67 表，WAL）。跨库账号键是 `users.openid`。
3. 原服务实际 Python **3.11.0rc1**，Studio **3.10.12**；生成器 current .venv 和 uvicorn 入口跨两个六月旧 release。Studio certifi/curl_cffi 的依赖 wheel 在 `/tmp`。仅复制 current 或安装默认 Python 会漏依赖。
4. 完整保留 `/opt/pindou` 的 46 + 74 历史发布、shared、backups、static-history、媒体和配置；约 66 万文件路径，很多 hardlink，源机整盘用约 32.5 GiB。全量历史不因迁移而删减；旧系统配置/日志/其他持久文件也做完整归档。
5. 当前正式 Tunnel 是远程 token 管理，本地 cloudflared YAML 已过期，不要直接启用那份 YAML。**正式 token 不得在新旧两机同时启动**；新机预演用隔离入口。
6. Studio 一启动就有通知/对账/import workers。演练必须隔离真实出站、凭据、队列，不能发送真实通知或消费生产支付。Mac customer / owner_alert 桥也会写库，最后停写要协调设备端并保留 outbox/幂等结果。
7. 1 条 queued 顾客通知和 1 条 unknown SMS 是调查时点的真实待处理状态，不得清空或全部标 sent。店主授权记录保持真实值，不再次运行已停止的累计授权脚本。
8. 系统有 enabled 但缺目录的 recharge-server 遗留 unit，归档并注明；不能把它误当作有效业务自动迁到新机启动。无须切换到 ApiSell 项目处理它。
9. 网站生成器仍需保留；小程序独立店铺版本已经去除旧 AI 页面，不要因迁移把它重新引入小程序。不要重建用户身份、积分、预约或模板。
10. Turnitin 的历史经验是先异机完整备份、预同步、恢复演练，最后共同停写做最终增量；不要把逐文件跨境 stat / 全量哈希放在停机窗口。

## 本任务接下来应完成

按执行手册持续推进：刷新必要生产状态 → 配置安全的源/目标传输和独立完整备份 → 目标隔离恢复（包括准确运行时）→ 预同步与全量文件/两库/关联验证 → 确定维护窗口 → 停止全部写入者后做最终一致副本和增量 → 单机切换 → 网站/小程序/后台/通知/设备链路验收 → 保留回退并更新运维目标。

用户已授权开始迁移，不因旧调查文档写着“尚未授权迁移”反复询问。购买额外付费资源、销毁旧机/历史数据、对真实顾客额外发测试通知不在这次授权中。必要的正常备份、安装依赖、目标配置、演练、同步和验证可直接推进。需要用户本人扫码或缺少第三方登录时再说明具体缺口；继续独立工作。

**回退边界**：新应用启动就可能写库。新机产生任何状态后，回退必须冻结新机，把两库/文件/通知结果的最新状态反同步，不能直接启用旧快照。提前验证异机备份可恢复，不能只有复制成功。当前已验证的功能规则全部延续，包含管理员代建/补录不送自助积分、短于两小时空档关闭、刚好两小时仍可预约。

每阶段把实测和剩余工作写入 `07_ops/PINDOU_FULL_MIGRATION_EXECUTION_20260918.md`，避免将计划写成完成。用户喜欢简明中文进度；完整清单/日志留在文件。不要让超过一分钟的同步/校验阻碍发进度；长任务后台运行并保存阶段状态。保持此任务使用 chatgpt-web/pro，不默认切回高用量模型。
