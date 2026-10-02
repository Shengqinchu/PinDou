# 店主大冲锋回国线路配置

2026-09-29（Toronto），用户明确授权同时配置 PinDou 上海服务器与本机 Clash。

## 服务器

- 目标：`36.139.201.94`，hostname `19558948263`；使用现有 `cnproxy` 专用账户。
- 原 `PermitOpen *:80 *:443 *:8080 *:8443` 不能连接游戏 15000 端口。改为 `PermitOpen any`，保留公钥认证、nologin、禁止交互 shell 与远程转发、内网 owner 防火墙及 5 Mbit/s SSH 限速。
- 没有新增监听端口、服务或公网防火墙放行，也没有修改业务代码、数据及 release。
- 备份：`/root/sshd_config.before-cnproxy-game-20260930T045359`。
- `sshd -t` 通过；普通 `pindou` 运维账户的生效 SSH 配置逐字保持不变；仅 reload ssh。
- 改前 SHA-256：`29480d3497c073953ada87a9517d0198b1aac3c8b1bce02a177215607ea093d6`。
- 改后 SHA-256：`fbedbb52737734b24160ee0d511d1323bd3445bd305cc227e100b23c391985e2`。

## 本机

配置位于 `C:/Users/123/Documents/回国VPN`，Clash 登记 `DCFShanghaiGlobal`（全局）与 `DCFShanghaiGame`（游戏分流）两个本地配置。原订阅与当前选择保留。原设置备份目录 `备份-游戏配置前-20260929-165613`。

`C:/Users/123/Desktop/应用中心/DCF` 有开启全局、开启分流、关闭线路三个快捷方式，使用已安装的 Mihomo 内核；通过正常 Windows UAC 启动 TUN，默认两小时自动停止，无开机启动。配置含专用回国账户私钥，只在用户本机保存，不进入本项目或 Git。

## 验证与边界

- 全局 TUN 的普通应用出口确认为 `36.139.201.94` 上海移动；公告 HTTPS 200；游戏 `180.188.19.44:15000` 返回协议数据。
- 实际启动器与游戏的连接日志均显示走 GLOBAL 上海节点；客户端短暂出现空白昵称页，无创建角色、进大厅或对局验收。
- SSH 节点不支持 UDP；启动器向 `124.221.231.248:7788` 的 UDP 请求失败，具体功能未确认。全局线路也会导致部分海外应用连接超时。
- 后续分流运行及延长游戏观察的命令被自动审批拒绝，只有 `blocked by policy`，未说明具体原因。没有绕过或改方式重试。
- 全局测试已停止，专用路由和内核已撤除，客户端保留配置但不常驻运行。
- 收尾时 `ssh`、`cnproxy-guard`、`pindou`、`pindou-studio`、`nginx`、`cloudflared` 全部 active，限速仍为 5 Mbit/s。PinDou 官网 HTTP 200，约 0.33 秒。

完整本机证据：`C:/Users/123/Desktop/应用中心/DCF/artifacts/mainland_test_20260929/配置与验收.md`，以及同目录 JSON、游戏截图和仅保留游戏相关连接的日志。

## 回退

如需撤回本次服务器修改，应先比对当前配置与上述改后哈希。如果后续已有他人修改，只将 cnproxy 的 `PermitOpen any` 恢复为原四个网页端口，不能覆盖其他改动。完成 `sshd -t` 后 reload ssh，复核 cnproxy 和普通运维账户的生效配置。客户端关闭线路即可停用，无需改动业务服务。
