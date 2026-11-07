# 小狗拼豆铺服务器资产

更新：2026-11-07（服务器加固、每日备份，见 [记录](SERVER_HARDENING_BACKUP_20261107.md)）。**默认生产服务器为 `36.139.201.94`**；以后排查、备份和部署均使用此机。全项目共享总账为 `C:/Users/123/Desktop/apisell/服务器资产清单.md`，本文件是 PinDou 的运维入口。

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
| 正式服务 | `pindou.service`、`pindou-studio.service`、`nginx.service`、`cloudflared.service`（2026.10.7；旧版留在 `/usr/local/lib/cloudflared/`）；防护与备份：`pindou-firewall.service`、`fail2ban.service`、`pindou-backup.timer`；店主线路 `cnproxy-guard.service`。2026-11-07 复核均 active 且开机自启 |
| 内核 | 运行 5.15.0-185；**5.15.0-203 已安装，等店主定时间重启**（约 1–2 分钟停机） |

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

私钥、密码、生产 `.env` 和凭据包仅保存在本机受限目录及授权服务器中；GitHub 保存路径、公钥指纹和操作说明。

## 防护（2026-11-07 起）

| 项目 | 现状 |
|---|---|
| SSH 登录 | 只认密钥：密码登录 2026-10-23 关闭（`/etc/ssh/sshd_config.d/00-key-only.conf`）；`01-pindou-hardening.conf` 让 root 只能用密钥、登录等待 30 秒、关 X11。`MaxAuthTries` 保持 6，免得带多把 key 的客户端被拒。忘带 key 时用移动云控制台 VNC，root 本地密码仍在 |
| fail2ban | `jail.d/pindou-sshd.local`：10 分钟内 5 次失败封 1 小时，屡犯递增到 1 周；normal 模式不把密钥试探算作失败。误封时 `fail2ban-client set sshd unbanip <IP>` |
| 入站防火墙 | `pindou-firewall.service`（脚本 `/usr/local/sbin/pindou-firewall`，源 `07_ops/pindou_firewall.sh`）：IPv4/IPv6 只放行 22、ICMP、DHCP 和回包，其余丢弃；不碰 OUTPUT，cnproxy-guard 规则不受影响。网站只经出站 Tunnel，不需入站端口。停用 `systemctl disable --now pindou-firewall` |
| 已关服务 | rpcbind（原监听公网 111）已停用并 mask |
| 系统更新 | 每天 02:30 Toronto 自动装安全更新（`20auto-upgrades`、`52pindou-unattended`、apt-daily-upgrade 定时器 drop-in），**不自动重启**；内核更新要店主定时间重启 |
| 云厂商自带 | 账户 `y19558948263`（cloud-init 默认，免密 sudo，`authorized_keys` 为空，SSH 只认密钥所以登不进）；`unionagent`（移动云助手）和 `titanagent`（自带 legacy iptables 链 `S_TITAN_INPUT`）。均未改动 |

## 店主回国浏览与游戏隧道（2026-09-29 更新）

店主在加拿大访问国内网站及排查大冲锋登录用。复用 SSH 22 端口，未在安全组开新端口。该 SSH 节点仅支持 TCP，不支持 UDP；游戏对局与语音尚未验收。

| 项目 | 值 |
|---|---|
| 服务器账户 | `cnproxy`（系统用户，shell `/usr/sbin/nologin`，家目录 `/var/lib/cnproxy`）；`authorized_keys` 带 `restrict,port-forwarding` |
| sshd 限制 | `/etc/ssh/sshd_config` 末尾 `Match User cnproxy`：仅公钥、禁 TTY/Agent/X11/SSH 隧道设备、`ForceCommand /usr/sbin/nologin`、`AllowTcpForwarding local`、`PermitOpen any`；2026-09-29 经用户授权解除原网页端口白名单，保留 owner 防火墙内网限制。改前备份 `/root/sshd_config.before-cnproxy-game-20260930T045359`，仅 reload ssh；原始账户创建前备份 `/root/sshd_config.before-cnproxy-20260927` |
| 防护与限速 | `cnproxy-guard.service` → `/usr/local/sbin/cnproxy-guard`：iptables owner 规则拒绝该账户访问 127/8、10/8、172.16/12、192.168/16、100.64/10、169.254/16 及全部 IPv6；eth0 HTB 将源端口 22 的出站限在 5 Mbit/s（保底 1 Mbit/s），其余流量不限 |
| 本机私钥 | `C:/Users/123/.ssh/pindou_cnproxy_ed25519`，指纹 `SHA256:ZE/FO+37Dxec4uGYqTgO1RDdoMYXhfZNwCSojwoVu1s`；Clash 配置 `C:/Users/123/Documents/回国VPN/回国-上海.yaml` 内嵌同一私钥，不入 Git |
| 手机私钥 | `C:/Users/123/.ssh/pindou_cnproxy_phone_ed25519`，指纹 `SHA256:8yww/AG/0nuJ13lSq7vlIpIx/fKn7mQeRQysZPK/YUM`；手机配置 `C:/Users/123/Documents/回国VPN/回国-上海-手机.yaml`（含 fake-ip DNS）。手机丢失时只从 `/var/lib/cnproxy/.ssh/authorized_keys` 删除注释为 `cnproxy-phone@pindou-prod 20260927` 的一行 |
| 客户端 | Clash Verge Rev（mihomo `type: ssh`，固定 `ssh-ed25519` 主机密钥）；`GEOSITE cn` / `GEOIP CN` 走上海，其余直连 |
| 游戏客户端配置 | 本机 `Documents/回国VPN/回国-上海-游戏全局.yaml`、`回国-上海-游戏分流.yaml`；Clash 已登记两个本地配置。原 DCF 目录里的开启/关闭线路快捷方式已随大冲锋停办删除（2026-10-18）；正常 UAC 启动 TUN，两小时自动关闭。原订阅不变；文件含专用账户私钥，不入 Git |
| 游戏线路实测（2026-09-29） | 全局 TUN 的公网出口为上海，公告 HTTPS 200、游戏 TCP 成功；实际客户端短暂到达昵称页，未创建角色/进大厅。分流仅完成配置与语法检查；详见 [运维记录](CNPROXY_GAME_CONFIGURATION_20260929.md) |
| 实测 | 出口“中国 上海 移动”；百度、B站、爱奇艺、腾讯视频、抖音、淘宝、网易云音乐 200；国内镜像约 330–470 KB/s；本机/内网端口被拒；下载期间小店 0.3 s 正常 |
| 手机订阅 | nginx `pindou-staging` 中 `location = /cn-sub/<随机令牌>`（位于 studio_deploy.py 管理区块之后，发布不会覆盖），返回 `/etc/nginx/cnproxy-sub/profile.yaml`（手机配置，root:www-data 640），no-store / noindex，经 Cloudflare 不缓存；完整地址只保存在本机 `C:/Users/123/Documents/回国VPN/订阅地址.txt`。改前备份 `/root/pindou-staging.before-cnsub-20260927`。泄露时删除该 location 或换令牌，并作废手机密钥 |
| 停用 | `systemctl disable --now cnproxy-guard`，删除 sshd 中的 `Match User cnproxy` 块后 `sshd -t && systemctl reload ssh`，`userdel -r cnproxy`；同时删除 `/cn-sub/` location 与 `/etc/nginx/cnproxy-sub` |

仅限店主本人使用，不向他人提供。22 端口持续有暴力登录尝试（2026-11-06 一天约 4,900 次、273 个 IP），已由 fail2ban 封禁；该账户只用密钥，不受影响。`PermitOpen any` 是为大冲锋放开的，游戏已停办；是否收回原四个网页端口 `*:80 *:443 *:8080 *:8443` 待店主决定（会影响店主自己的线路）。

## 大冲锋附属物（2026-10-18 已全部清理）

店主的大冲锋私服已停办。2026-10-18 已停用并删除本机上的大冲锋相关项，PinDou、PinDou Studio、nginx 删除后仍为 active：
- 回环测试服：`dcf-lab-channel.service`、系统用户 `dcflab`（含 `/home/dcflab`）、`/home/pindou/finalcombat-lab`、`/home/pindou/finalcombat-friend-lab`（16G）、`/home/pindou/dcf-ipc`。
- 加速通道：`xcz-hy2.service`（Hysteria2，UDP 29911，ACL 只放行极光 tcp/25443）、系统用户 `xczhy`、`/opt/xcz-hy2`。

2026-11-07 收尾：`/home/pindou` 的 ACL 按当初快照恢复（无附加条目）；删除空组 `dcflab`（`pindou` 已移出）；`/root/dcflab-before-20261003/` 打包到 `/var/backups/pindou/legacy/dcflab-before-20261003.tar.gz` 后删除。没有其他大冲锋残留。

## 业务与备份位置

| 对象 | 位置 |
|---|---|
| 生成器 current | `/opt/pindou/current` → `releases/20261107101920-pattern-threads`（图纸生成移出事件循环；回退 `20261017142309-timecard-offsale`）。`.venv` 链到 `releases/20260615074539-wallet-mode-labels`，该 release 不能删 |
| Studio current | `/opt/pindou/studio/current` → `releases/20261021235529-studio-v7`；以 [部署说明](deployment.md) 顶部为准 |
| 生成器数据库 / 环境 | `/opt/pindou/shared/var/pindou.db` / `/opt/pindou/shared/.env` |
| Studio 数据库 / 环境 | `/opt/pindou/studio/shared/studio.sqlite3` / `/opt/pindou/studio/shared/.env` |
| 图片与资料 | 两个 `shared` 目录、`/opt/pindou/shared/data`、Studio `shared/media`、全部历史 release / static-history 保留 |
| 每日备份 | `pindou-backup.timer` 每天 03:30 Toronto → `/var/backups/pindou/daily/<时间>/`（root 700）：两库在线备份并 `integrity_check`、两个 shared 目录、服务配置、`manifest.json`；未变文件硬链接上一份。保留 14 天 + 每月第一份留 6 个月；`latest` 指向最新。失败经 Server酱 通知店主。脚本源 `07_ops/pindou_backup.sh` |
| 离机副本 | 本机 `C:/Users/123/Desktop/PinDou/artifacts/server-backups/`（Git 忽略）；2026-11-07 首份已拉回并核对哈希。定期离机复制待店主决定 |
| 新机迁移归档 | `/root/pindou-migration-20260918` |
| 本机独立副本 | `D:/Users/123/Documents/PinDouBackups/20260918`，索引 `MIGRATION_BACKUP_INDEX.json` |

迁移副本已完成哈希及恢复验证；它覆盖切换时点。2026-11-07 起由每日备份接续，恢复步骤见 [加固与备份记录](SERVER_HARDENING_BACKUP_20261107.md)。生成器 Python 3.11.0rc1 与 Studio Python 3.10.12、跨历史 release 的 venv 路径均按原样保留。新机 `/etc/gai.conf` 使用完整 precedence 表并优先 IPv4，避免不可达 IPv6 导致外部服务连接长时间等待。

2026-09-18 17:02 UTC 补齐 `/etc/hosts` 中本机名 `19558948263` 的 `127.0.1.1` 映射，保留原 `ecloud` 别名；修正新 SSH 入口验证时发现的 sudo 主机解析警告。原文件备份为 `/root/pindou-migration-20260918/target-hosts-before-name-fix`；地址解析及 pindou 免密 sudo 均通过，无业务服务重启。

## 旧服务器：仅回退资料

- IP `36.137.177.135`；主机名 `ecs-37487420`；原 key 为 `C:/Users/123/.ssh/pindou_prod_ed25519`。
- 用户提供到期时间：**2026-09-25 22:41:52 上海时间**，即 Toronto 10:41:52；当前账单未重查。
- 旧机应用和正式 Tunnel 已停止并禁用；不再承担生产，不作为后续部署默认目标。没有销毁旧实例或删除旧资料。
- 新机已有生产写入，回退必须先冻结新机、反向同步两库和全部最新业务文件及通知状态，再启动唯一的一组生产服务。不能直接重启旧快照，也不能双开正式 Tunnel / 通知消费者。

## 相关文档

- [服务器加固、每日备份与健康检查（2026-11-07）](SERVER_HARDENING_BACKUP_20261107.md)
- [布贴 DIY 独立预约发布核验](STUDIO_PATCH_BOOKING_RELEASE_20260928.md)
- [最新商品图片上传提速与画质取舍](STUDIO_IMAGE_UPLOAD_SPEED_20260924.md)
- [最新顾客消息与商品图片发布核验](STUDIO_MESSAGES_GALLERY_RELEASE_20260924.md)
- [当前部署说明](deployment.md)
- [最新后台功能发布核验](STUDIO_ADMIN_CONTROLS_20260918.md)
- [最新店铺发布核验](STUDIO_SHOP_CHECKOUT_20260923.md)
- [最新订单与账号发布核验](STUDIO_ORDERS_ACCOUNT_20260923.md)
- [迁移验收与备份校验](PINDOU_FULL_MIGRATION_ACCEPTANCE_20260918.md)
- [迁移执行记录](PINDOU_FULL_MIGRATION_EXECUTION_20260918.md)
- [迁移与回退手册](PINDOU_FULL_MIGRATION_RUNBOOK_20260918.md)

变更服务器、密钥、期限或服务角色时，同步更新此文件、共享资产清单、本机 `.env` / SSH 别名以及 GitHub 文档。日期来自用户确认/截图，硬件和运行状态来自带时间的实测，后续变更需再次核对。
