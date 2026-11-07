# 服务器加固、每日备份与健康检查（2026-11-07）

店主 2026-11-06 晚（Toronto）：“把以往的问题解决一下 / 做一下服务器健康检查”，随后“对于对服务器的保护 我们在服务器资产md里面有相关内容 看看要不要做”。目标 `36.139.201.94`，主机名 `19558948263`。下文时间为上海时间 2026-11-07（Toronto 前一晚 20:40 起）。

## 健康检查（只读）

- 系统：运行 49 天，负载 0.2 / 8 核，内存约 0.8 / 16 GB，磁盘 52%（余 37 GB），inode 15%；无 OOM、无内核错误，NTP 同步。
- 服务：`pindou`、`pindou-studio`、`nginx`、`cloudflared`、`cnproxy-guard`、`ssh` 均 active；14 天内四个业务服务无 warning 以上日志，无 failed unit。10-31 04:25 两个应用的重启来自另一个会话的 root 登录（只读的虎皮椒对账，1 单正常）。
- 数据：两库 `quick_check` ok（Studio WAL，生成器 delete-journal）。近 30 天预约完成 21、取消 5；14 天通知（邮件、短信、微信、Server酱）无错误，两个短信桥心跳正常。生成器 116 件作品（14 天新增 17），30 天无订单。
- 公网：主要页面 200，约 0.3–0.45 秒；域名经 Cloudflare 注册，到期 2027-06-01。
- 测试：生成器后端 123 项全过；小程序脚本全过；Studio 649 过、1 项失败（过时测试，已修，见下）。
- 发现的问题（以前各次检查遗留）：无 fail2ban、rpcbind 对公网开 111、无定时备份、系统更新自 09-18 起未装（刷新源后共 170 个包待升级）、自动安全更新被关闭、大冲锋零星残留；另外小程序通知环境仍是体验版（见第 1 条）。

## 已处理

1. **小程序通知改为正式版。** Studio `.env` 的 `STUDIO_MINIAPP_ENV` 从 `trial` 改为 `release`。顾客预约卡片、店主卡片、店主绑定码和网站扫码登录原来都打开体验版，普通顾客点不开；正式版 0.1.33 自 10-17 已上线，原计划“正式包可用后切 release”一直没做。先用微信接口按正式版、`check_path=true` 生成 `pages/studio/owner` 与 `pages/auth/studio-confirm` 的码，两个页面都通过；重启 `pindou-studio` 后进程环境为 release，`/studio-api/health` 200。改前备份 `/opt/pindou/studio/shared/.env.before-miniapp-release-20261107095935`（root 600）。回退：恢复该文件并重启 `pindou-studio`。
2. **大冲锋残留。** `/home/pindou` 的 ACL 按 `/root/dcflab-before-20261003/home-pindou.facl` 恢复为无附加条目；`pindou` 移出并删除空组 `dcflab`（无任何文件属于该组）；回退资料目录打包到 `/var/backups/pindou/legacy/dcflab-before-20261003.tar.gz` 后删除。
3. **rpcbind。** 无 NFS 挂载、`rpcinfo` 只有 portmapper；`rpcbind.socket`/`rpcbind.service` 停用并 mask，外部探测 111 不再开放。回退：`systemctl unmask rpcbind.socket rpcbind.service && systemctl enable --now rpcbind.socket`。
4. **SSH。** 密码登录已于 10-23 关闭（`00-key-only.conf`）。新增 `/etc/ssh/sshd_config.d/01-pindou-hardening.conf`：`PermitRootLogin prohibit-password`、`LoginGraceTime 30`、`X11Forwarding no`。`MaxAuthTries` 保持 6，带多把 key 的客户端不至于被拒。`sshd -T -C user=cnproxy` 确认店主线路的 Match 块不变。应用时设 4 分钟自动撤回，用新连接验证 root、pindou（paramiko 与 `ssh pindou-prod`/`pindou-prod-root`）后才取消撤回。回退：删除该文件，`sshd -t && systemctl reload ssh`。
5. **fail2ban。** `/etc/fail2ban/jail.d/pindou-sshd.local`：normal 模式、10 分钟 5 次失败封 1 小时，`bantime.increment` 屡犯递增到 1 周；`fail2ban.d/pindou.local` 把封禁历史保留 8 天。启用前用前 24 小时日志预演：攻击 IP 254 个，会被封 155 个，店主和运维登录用的家庭宽带网段没有一次命中；normal 模式不把合法用户的密钥试探算作失败。同样带 4 分钟自动撤回，验证新登录后取消。误封：`fail2ban-client set sshd unbanip <IP>`；被锁在外面时用移动云控制台 VNC。
6. **入站防火墙。** 新增 `pindou-firewall.service`（`/usr/local/sbin/pindou-firewall`，源 [pindou_firewall.sh](pindou_firewall.sh)、[unit](pindou_firewall.service)），IPv4 和 IPv6 的 INPUT 只放行本机回环、已建立连接的回包、tcp/22、ICMP、DHCP，其余丢弃；fail2ban 链在它之前。没用 ufw：ufw 会在 OUTPUT 先放行回环流量，绕过 `cnproxy-guard` 对店主线路的内网限制；本脚本不碰 OUTPUT。云安全组本来就挡着 80/443，这是第二层：以后哪个服务误监听公网（像 rpcbind）也到不了。外部探测 22 开放，80/443/8000/8011/111 均不通；网站经 Tunnel 200，出站访问微信接口、Server酱、NTP 正常。同样带自动撤回，验证后才设为开机启动。回退：`systemctl disable --now pindou-firewall`。
7. **系统更新。** `apt-get dist-upgrade`（保留现有配置文件）装了 170 个包，含 libc6、systemd、openssl/libssl3、openssh、sudo、nginx 和内核 5.15.0-203。用 `systemd-run` 脱离 SSH 会话执行，避免断线打断 dpkg；日志 `/root/apt-dist-upgrade-20261107.log`，升级前包清单 `/root/dpkg-before-20261107.txt`。nginx 随包重启，`pindou`、`cloudflared` 随下文发布重启；新内核和其余进程的新库要重启服务器才生效（见“待店主决定”）。
8. **自动安全更新。** `20auto-upgrades` 两项由 "0" 改为 "1"（原文件备份 `/root/20auto-upgrades.before-20261107`）；`52pindou-unattended` 设为不自动重启、清理旧内核；`apt-daily-upgrade.timer` drop-in 改到每天 02:30 Toronto（原为上海 06:00，即 Toronto 傍晚）。来源沿用 Ubuntu 默认（release 与 security）。
9. **每日备份。** `pindou-backup.timer`（每天 03:30 Toronto，随机延后 10 分钟内，关机错过会补跑）运行 `/usr/local/sbin/pindou-backup`（源 [pindou_backup.sh](pindou_backup.sh)，unit 见 [pindou_backup_units.txt](pindou_backup_units.txt)），写到 `/var/backups/pindou/daily/<时间>/`：
   - `db/`：以 `pindou` 用户经 SQLite backup API 在线复制两库（不在活库旁留下 root 的 -wal/-shm），逐个 `integrity_check`；
   - `files/`：两个 shared 目录（不含活库文件）以及 cloudflared、nginx、ssh、fail2ban、apt、systemd unit、`/usr/local/sbin`、各账户 `authorized_keys`、crontab；未变文件硬链接上一份，每天只多占变化部分；
   - `manifest.json`：两库哈希、表数、当时 release。
   保留 14 份日备份，每月第一份另留 6 个月；目录 root 700。失败时 `pindou-backup-alert.service`（源 [pindou_backup_alert.py](pindou_backup_alert.py)）用 Studio 店主 Server酱 key 通知店主，只发失败提示。首份 2026-11-07 10:11:40，耗时 4 秒、327 MB，两库 integrity ok。
10. **离机副本。** 首份快照已拉回本机 `artifacts/server-backups/20261107-101140`（Git 忽略）并核对两库哈希。没有设定期离机复制（见“待店主决定”）。
11. **cloudflared 2026.10.4 → 2026.10.7。** 官方 release，SHA-256 `1f99fb518b83dec2ba8d870a7cc991d82a77e6196295a3d2754ba17ab9f91872` 与发布页一致；变化为依赖安全更新（go-chi、go-jose）、HTTP/2 并发流回归修复与启动检查调整。旧二进制留在 `/usr/local/lib/cloudflared/cloudflared-2026.10.4`。重启后几秒内恢复服务，lax 机房 3 条连接（第 4 条在重连），公网 200。启动检查里 region2 的 QUIC/HTTP2 失败在 10-27（旧版、无防火墙）就有，是线路问题；防火墙开关两种状态下 region2 的 TCP 7844 都能连通。回退：把旧二进制装回 `/usr/bin/cloudflared` 并重启。
12. **图纸生成不再卡住生成器服务。** 生成器只有一个 Uvicorn 进程，`/generate/script` 原来在事件循环里同步出图，本机实测一张 1.5–7 秒，期间网站和小程序的生成器请求全部排队。现在构建、保存、出图放进工作线程，最多两张同时生成（[generate.py](../06_backend/pindou/api/generate.py)，新增测试确认不在事件循环线程执行；后端 124 项全过）。发布 `20261107101920-pattern-threads`：由 `20261017142309-timecard-offsale` 硬链接复制，只换这一个文件，先核对生产旧文件与 Git 一致，健康检查失败自动回退，`ROLLBACK_TO` 指向上一版。公网实测游客设备生成 104×104 返回 200（含跨洋上传共 23.8 秒），期间 `/health` 中位 0.36 秒、最慢 0.70 秒（平时 0.30 秒）；测试作品已删除。
13. **过时测试。** Studio `test_default_profile_names.py` 把 `拼豆用户` 当自定义名，但代码有意给这个占位名加后缀（`test_customer_identity.py` 覆盖），已删去该项，相关 8 项通过。
14. **账号绑定冲突复查。** 只读查询 `studio_miniapp_binding_conflicts` 为空，09-29 恢复后没有新冲突。

## 恢复备份

1. 先停写：`systemctl stop pindou pindou-studio`，必要时暂停 Mac 短信桥。
2. 取 `/var/backups/pindou/daily/<时间>/db/` 的两库，核对 `manifest.json` 中的哈希，各自复制回 `/opt/pindou/studio/shared/studio.sqlite3`、`/opt/pindou/shared/var/pindou.db`，属主 `pindou`；删掉活库旁残留的 `-wal`/`-shm`。
3. 需要时用 `rsync -a` 从 `files/opt/pindou/...` 还原图片与 shared 文件。
4. 启动服务，检查健康接口和公网页面。

## 待店主决定

- **重启服务器**：启用内核 5.15.0-203 和已更新的库，约 1–2 分钟停机，建议闭店后。开机项已核对：`pindou`、`pindou-studio`、`nginx`、`cloudflared`、`cnproxy-guard`、`fail2ban`、`pindou-firewall` 均开机自启，`cnproxy-guard` 启动时重建限速和内网限制，GRUB 默认项为新内核。
- **店主线路 `PermitOpen any`**：为大冲锋放开，游戏已停办；建议收回原四个网页端口，9 月实测这四个端口下常用国内网站都正常。
- **定期离机备份**：本机定时拉取（电脑要开着），或云存储（需店主开通）。

## 未动

- 旧 release（生成器约 16 GB）：空间充足，暂不清理；`20260615074539-wallet-mode-labels` 是 7 个 release 的 venv 来源，任何时候都不能删。
- journal 2.0 GB、迁移归档 3.6 GB：空间充足，保留。
- 云厂商账户 `y19558948263`、移动云助手、`titanagent`：保持原样。
