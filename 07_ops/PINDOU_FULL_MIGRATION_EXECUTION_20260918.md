# PinDou 完整迁移执行记录

## 完成状态（2026-09-18）

正式服务已切至 `36.139.201.94`，12:20:35 Toronto 完成公网验收。完整范围、数据校验、功能测试、离机备份及回退限制见 [迁移验收](PINDOU_FULL_MIGRATION_ACCEPTANCE_20260918.md)。下方保留执行过程中的历史状态，不代表当前仍未迁移。

- 最终源/目标 734,021 条全树清单差异为 0，两套数据库全 17 + 67 张表逻辑指纹一致。
- 123 项隔离回归、44 项上线后接口及 12 项公网检查通过；恢复演练保留新预约且管理员代录不送积分。
- 旧机应用及 Tunnel 已停止并禁止开机启动，新机仅一套正式消费者；Mac 短信桥恢复原进程及 outbox。
- 生产 `.env` 更新至新主机/key，root 与 pindou 登录验证通过；历史 release、资产、资料、配置及原主机持久文件归档全部保留。
- 新机已开始写入，回退必须反向同步新状态，不能直接启动旧冻结快照。

## 2026-09-18 14:47 UTC 起：主任务正式执行迁移

用户追加明确指令“那你来迁移吧”，由本任务接手。Web Pro 任务已结束、两个相关进程均不存在，无并行迁移执行者。此前只读边界已被此次完整迁移授权取代；不需要重新确认一般备份、恢复、停写和切换步骤。

当前阶段：**归档、离机备份与新机预同步进行中，尚未停写或切流量。**

截至 15:46 UTC 的新增实证：

- 整根归档原始 tar 流为 34,541,813,760 字节。无损重压缩文件 2,947,750,372 字节，SHA-256 `7044eb47b2f3287956865175c29d08f14ee0267fd5fd1c2bfa3159e620f2e9f6`。
- 15:41:35 UTC，完整归档已独立下载至 `D:/Users/123/Documents/PinDouBackups/20260918/source-full-root-compact.tar.zst` 并校验相同 SHA-256。
- 15:45:47 UTC，本机完整解压读取后的 tar 流 SHA-256 与源机原始 11.16 GB 归档解压流一致：`3b0aebc7dd0be911cc2a57b78d9bd629757724d84698465f1430089a31ae31aa`，证明重压缩没有遗漏资料。证明文件在同目录 `independent-full-root-verification.json`。
- tar 归档过程中只有运行中 syslog 变化和一个运行时 socket 忽略警告；zstd 完整性通过。最终业务冻结副本、系统日志增量仍需补齐，不把在线全根归档当作共同停写数据库备份。
- 源业务全树清单完成：734,018 个路径条目、523,677 个独立文件 inode、19,343,058,374 个独立数据字节，无扫描错误或扫描中变化。目标初次全量复制仍在运行。
- 15:29 UTC，新机微信 `stable_token` 请求成功，`force_refresh=false`；Authing 公钥可读。没有发送消息或消耗订阅授权。新旧机器均能加载 DejaVu Sans / Sans Mono 字体。
- 源线上 27 个 Studio Python 模块与本地拟用回归测试对应的代码 SHA-256 全部相同。测试工具依赖安装在独立 QA venv，正式两个 venv 不改。
- 已准备且仅准备：短信桥暂停/恢复、旧机维护/停写、最终同步/全表指纹、目标运行配置安装与回退演练脚本。旧机尚未进入维护，Mac 两个实际发送进程继续正常运行；正式目标 Tunnel 尚未启动。

- 14:47 UTC 刷新确认：旧机两个应用、Nginx 和正式 Tunnel 均运行；新机尚无业务进程。两端均为 Ubuntu 22.04.5、8 CPU，目标磁盘可用约 66.74 GiB。
- 从旧机 `127.0.0.1:20241/config` 获取生效中的 Tunnel 配置。正式域名、www、staging 均指向 `https://localhost`，`noTLSVerify=true`，末尾 404 兜底。私有原始证据保存在 `artifacts/migration-research-20260918/private/source-live-refresh.json`。不使用旧的本地 YAML 推断正式路由。
- 旧机通过 SQLite backup API 分别生成两个在线一致副本，完整性检查及外键检查通过；它们不是最终共同停写副本。
- 旧机 `pindou-migration-archive.service` 正在制作整根文件系统的 tar.zst，保留 ACL、xattr、numeric UID/GID、稀疏文件、硬链接和软链接。排除 /proc、/sys、/dev、/run 等运行时虚拟挂载及本次归档输出目录，避免递归归档自身。最终需检查 tar 警告、zstd 检测和 SHA256。
- 本机离机备份目录：`D:/Users/123/Documents/PinDouBackups/20260918`，限制 ACL，仅当前用户访问。后台持续下载归档并在完成后核对 SHA256。原拟 D:/Backups 目录不可写，未改变其权限，改用本人 Documents 下目录。
- 目标机已启用临时、固定旧机主机指纹的迁移 SSH key。私网路由实测不可达，使用已验明身份的公网地址。`pindou-migration-precopy.service` 用 `rsync -aHAX --numeric-ids` 同步整个 `/opt/pindou`，不删源数据。
- 目标默认云用户原占用 UID/GID 1000，核验无其运行进程后迁至 1001，备份原账户文件；创建源业务同名 `pindou` UID/GID 1000，保持文件属主一致。只更改该云用户自身主目录属主，不全盘 chown。
- 新机已安装 Python 3.11.0rc1、Python 3.10.12、Nginx 1.18.0 及所需基础包。发行包补丁号与旧机不同，必须完成实际兼容测试；未声称二进制完全相同。业务和 Tunnel unit 持续 mask，Nginx 尚未公开服务。
- 已单独复制旧机 Nginx/systemd/Tunnel 配置、同版 cloudflared 二进制和在线 SQLite 副本至目标私有准备目录，没有启动正式 Tunnel。
- 源业务目录正在生成服务端批量 SHA256/元数据/硬链接清单，一 inode 只读一次，避免逐文件跨网络校验的长停机问题。
- Mac 两个短信桥的 SSH 管理及 launchd 配置可读取，后续在切换阶段阻止新领取、排空在途任务并暂停，仅针对 PinDou 桥，保留设备端 outbox 和游标。
- 支付方官方接口说明核实：只有正文 `success` 算回调成功，否则重试 6 次。停写期间不能伪造成功；最终切换仍需核对待支付订单和回调。来源：https://www.xunhupay.com/doc/api/pay.html。

执行证据和一次性脚本均位于 Git 忽略的 `artifacts/migration-research-20260918`；服务器准备目录为 `/root/pindou-migration-20260918`。后续状态须以实际检测更新，不能将后台任务启动当作迁移完成。

## 2026-09-18：新机访问与任务交接

- 用户授权：为新机配置 SSH key，并开始完整迁移；指定另开任务使用 ChatGPT Web — Pro。
- 源机：36.137.177.135。新机：36.139.201.94，root。
- 已完成新机独立 Ed25519 公钥安装，第二条独立连接密钥认证成功。私钥为 `C:/Users/123/.ssh/pindou_mobilecloud_20260918_ed25519`；主机指纹固定到 known_hosts。密码按要求存放于 `artifacts/migration-research-20260918/private/target-access.json`，不进入 Git。
- 新机：Ubuntu 22.04.5 x86_64、8 CPU、约 15.61 GiB RAM、78.56 GiB 根文件系统，可用约 66.74 GiB。详情 `artifacts/migration-research-20260918/target-bootstrap.json`。
- 新任务：`01a0b4f0-6568-7a80-a86e-f7fb931f80f2`，名称“PinDou 完整迁移到新移动云服务器”。通过支持的 Codex app-server 协议创建并持久保存，model/list 与 thread/start 均确认 `chatgpt-web/pro`；未更换全局模型配置。

## 新任务首轮结果：工具通道阻塞，迁移未开始

新任务先回复将读取交接材料、核对源/目标，随后报告：读取交接文件和查询当前工作目录两次 Codex Native 调用均被 OpenAI 工具安全检查拦截，未给出进一步拒绝理由。

父任务回读执行记录：首轮已结束，当前 rollout 未出现成功的原生命令执行记录；没有备份、文件同步、数据库恢复、旧机停写或 Tunnel 切换的完成证据。因此**不能把该任务的 turn completed 当成迁移完成或正在搬迁**。

父任务未禁用或绕过工具安全检查，未在别的模型中重复执行被拒绝的迁移步骤。新任务保留，等待其执行通道恢复后继续。SSH 配置成功与模型工具通道阻塞是两件不同的事。

当前唯一远程变更是新机 root 的 SSH 公钥配置；旧生产未改动，新机未启动正式应用或 Tunnel。完整异机备份、恢复演练、全量/增量同步和正式切换都尚未执行。

## 继续时

先读 [Web Pro 交接](PINDOU_MIGRATION_WEB_PRO_HANDOFF_20260918.md)及 [完整手册](PINDOU_FULL_MIGRATION_RUNBOOK_20260918.md)，核对最新源状态后从独立备份/预同步准备开始。既有迁移授权有效，不再次要求用户提供密码或授权普通准备步骤。需要解决的是本轮模型工具调用被拒，不能声称已有备份或迁移效果。
