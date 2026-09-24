# 小狗拼豆铺服务器资产

更新：2026-09-24。**默认生产服务器为 `36.139.201.94`**；以后排查、备份和部署均使用此机。全项目共享总账为 `C:/Users/123/Desktop/apisell/服务器资产清单.md`，本文件是 PinDou 的运维入口。

## 当前生产服务器

| 项目 | 配置 / 依据 |
|---|---|
| 云厂商 / 地区 | 移动云，华东-上海1，可用区一（2026-09-18 用户控制台截图） |
| 公网 IPv4 | `36.139.201.94` |
| 内网 IPv4 | `192.168.0.41` |
| 主机名 | `19558948263`；不是完整云实例 UUID |
| 操作系统 | Ubuntu 22.04.5 LTS，x86_64（SSH 实测） |
| CPU / 内存 | 8 vCPU / 标称 16GB；实测约 15.61 GiB |
| 系统盘 | 标称 80GB；根文件系统实测 84,356,640,768 bytes，约 78.56 GiB |
| 公网带宽 | 8 Mbps（控制台截图；不是吞吐测速结果） |
| 计费 / 续费方式 | 包年计费、手动续订（控制台截图） |
| 使用期限 | **2026-09-18 至 2027-09-18**，用户明确确认“今天起一年” |
| 到期时间 | **2027-09-18**；用户截图显示 `2027-09-18 21:23:25`。精确时分秒和控制台时区未重新登录账单确认，日历以用户确认的日期为准 |
| 正式域名 | `pindoupuppy.com`；兼容 `www.pindoupuppy.com`、`staging.pindoupuppy.com` |
| 生产切换 | 2026-09-18 16:20:35 UTC / 12:20:35 America/Toronto 公网验收完成 |
| 正式服务 | `pindou.service`、`pindou-studio.service`、`nginx.service`、`cloudflared.service`；2026-09-23 店铺发布复核均 active |

## 登录与密钥

| 项目 | 值 |
|---|---|
| 常规 SSH | `ssh pindou-prod`，用户 `pindou`，端口 22；原免密 sudo 角色已保留 |
| root 运维 SSH | `ssh pindou-prod-root`；现有需要 root 的发布脚本仍可使用同一新机、新 key |
| 私钥本机位置 | `C:/Users/123/.ssh/pindou_mobilecloud_20260918_ed25519` |
| 对应公钥 | 同路径加 `.pub` |
| 登录公钥指纹 | `SHA256:lHUCBJE12+OMh+W/Av7w/OOU900PxzuGI8wLmJJRwtg`（Ed25519） |
| 服务器 Ed25519 主机指纹 | `SHA256:vpubF8HbgFW+ig0UIWRfS9f4nij1ge5H2RBL5t1ddz4`；与登录公钥指纹不同 |
| 主机校验 | 本机 `C:/Users/123/.ssh/known_hosts`；两个别名均使用严格主机校验和指定 key |
| 本机部署配置 | 项目根 `.env`：`PINDOU_PROD_SSH_HOST=36.139.201.94`、`PINDOU_PROD_SSH_USER=pindou`、`PINDOU_PROD_SSH_KEY_PATH` 指向上述新 key |
| 密码本机存档 | `artifacts/migration-research-20260918/private/target-access.json`；Git 忽略 |

私钥、密码、生产 `.env` 和凭据包仅保存在本机受限目录及授权服务器中；GitHub 保存路径、公钥指纹和操作说明。新机保留原密码登录配置；不能把旧机曾禁用密码的历史记录当作新机现状。

## 业务与备份位置

| 对象 | 位置 |
|---|---|
| 生成器 current | `/opt/pindou/current` → `releases/20260910015453-studio-v7`（迁移验收时） |
| Studio current | `/opt/pindou/studio/current` → `releases/20260924155213-studio-v7`（2026-09-24 顾客消息与商品图片修正；[验收](STUDIO_MESSAGES_GALLERY_RELEASE_20260924.md)） |
| 生成器数据库 / 环境 | `/opt/pindou/shared/var/pindou.db` / `/opt/pindou/shared/.env` |
| Studio 数据库 / 环境 | `/opt/pindou/studio/shared/studio.sqlite3` / `/opt/pindou/studio/shared/.env` |
| 图片与资料 | 两个 `shared` 目录、`/opt/pindou/shared/data`、Studio `shared/media`、全部历史 release / static-history 保留 |
| 新机迁移归档 | `/root/pindou-migration-20260918` |
| 本机独立副本 | `D:/Users/123/Documents/PinDouBackups/20260918`，索引 `MIGRATION_BACKUP_INDEX.json` |

迁移副本已完成哈希及恢复验证；它覆盖切换时点，不能替代之后的持续备份。生成器 Python 3.11.0rc1 与 Studio Python 3.10.12、跨历史 release 的 venv 路径均按原样保留。新机 `/etc/gai.conf` 使用完整 precedence 表并优先 IPv4，避免不可达 IPv6 导致外部服务连接长时间等待。

2026-09-18 17:02 UTC 补齐 `/etc/hosts` 中本机名 `19558948263` 的 `127.0.1.1` 映射，保留原 `ecloud` 别名；修正新 SSH 入口验证时发现的 sudo 主机解析警告。原文件备份为 `/root/pindou-migration-20260918/target-hosts-before-name-fix`；地址解析及 pindou 免密 sudo 均通过，无业务服务重启。

## 旧服务器：仅回退资料

- IP `36.137.177.135`；主机名 `ecs-37487420`；原 key 为 `C:/Users/123/.ssh/pindou_prod_ed25519`。
- 用户提供到期时间：**2026-09-25 22:41:52 上海时间**，即 Toronto 10:41:52；当前账单未重查。
- 旧机应用和正式 Tunnel 已停止并禁用；不再承担生产，不作为后续部署默认目标。没有销毁旧实例或删除旧资料。
- 新机已有生产写入，回退必须先冻结新机、反向同步两库和全部最新业务文件及通知状态，再启动唯一的一组生产服务。不能直接重启旧快照，也不能双开正式 Tunnel / 通知消费者。

## 相关文档

- [最新顾客消息与商品图片发布核验](STUDIO_MESSAGES_GALLERY_RELEASE_20260924.md)
- [当前部署说明](deployment.md)
- [最新后台功能发布核验](STUDIO_ADMIN_CONTROLS_20260918.md)
- [最新店铺发布核验](STUDIO_SHOP_CHECKOUT_20260923.md)
- [最新订单与账号发布核验](STUDIO_ORDERS_ACCOUNT_20260923.md)
- [迁移验收与备份校验](PINDOU_FULL_MIGRATION_ACCEPTANCE_20260918.md)
- [迁移执行记录](PINDOU_FULL_MIGRATION_EXECUTION_20260918.md)
- [迁移与回退手册](PINDOU_FULL_MIGRATION_RUNBOOK_20260918.md)

变更服务器、密钥、期限或服务角色时，同步更新此文件、共享资产清单、本机 `.env` / SSH 别名以及 GitHub 文档。日期来自用户确认/截图，硬件和运行状态来自带时间的实测，后续变更需再次核对。
