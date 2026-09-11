# CTExcel / iPhone / Mac 短信测试准备

2026-09-11。店主确认 CTExcel 主卡继续在日常 iPhone 中，并有可长期开机、使用同一 Apple 账号的 Mac。按 [消息方案](../01_research/tech/STUDIO_MESSAGING_PLAN_20260911.md) 完成设备准备和一次 +86 短信实收测试，不代表预约短信已上线。

## 已完成

- 通过既有 `macmini` SSH 配置实际连通 Mac mini：macOS 15.6、arm64、当前桌面用户 chix。
- 已安装 `/opt/homebrew/bin/imsg` 0.4.0；`send --help` 确认支持 `--service sms`、E.164 收件人、JSON 输出。保留原有工具版本，没有升级全局 Homebrew 工具或修改其他服务。
- 新增 `07_ops/mac_sms_probe.py`，复制到 Mac 的 `~/Library/Application Support/PinDouSMS/mac_sms_probe.py`；目录 0700，脚本 0600。默认只检查工具，只有显式 `--send-approved-test` 才可能调用发送。
- 检查工具可执行通过。7 项离线测试通过：授权文案/时间/号码校验、SMS 路由、结果脱敏、重复请求、超时及进程中断后不重发。离线收件人是虚构号码、发送程序为模拟。
- 已打开 Mac 的“信息”App，供店主确认 Apple 账号和设备设置。未读取聊天记录或联系人。
- 发起过一次只读 AppleScript 服务数量检查，18 秒未返回而终止；只能记录为“等待 macOS 权限或应用响应”，不能据此宣称已经授权、未登录或短信转发已开启。

设备准备阶段没有发送真实短信。随后完成下述一次明确授权的发送尝试；没有创建或更改顾客预约、没有安装自动启动发送服务，也没有开放 Mac 的公共发送端口。

## 单条测试进展

2026-09-11，店主回复已开启设置，并提供一个 +86 测试号码。已按原先约定文案发起一次 SMS 发送尝试，随后店主确认“收到了，发件人是我的加拿大号码”。**本次 Mac → iPhone → CTExcel → +86 的单条短信实收测试通过**；号码仅保存于 Mac 的私有 `test-recipient.json`（0600），不进入 Git。

- 测试前核对已安装脚本的 SHA-256 与准备版本一致。
- 发送工具没有给出可确认的成功结果，原始日志保留 `outcome_unknown`。收件人后续明确确认收到及发件号码，另存私有 `test-confirmation.json`（0600），与工具结果分开记录；不把人工确认伪装成运营商回执。
- 已只读核对本次请求日志；同一请求不会再次触发发送，没有重发或另行发送其他文案。
- 这次发送成功不证明掉线、休眠、重启、多号码切换、加拿大本地收件等场景均可用。Mac 权限弹窗是否显示未单独核实；短信实收不需要以该问题的回答为前提。

下一步接入预约业务事件与顾客通知偏好。当前没有预约自动短信；后续必须保留发送前持久化、同一事件去重、结果不确定时不重发、过期提醒停止发送，并在后台区分工具结果与收件人确认。

## 后续收发账号与后台要求

店主最新要求优先使用女朋友的手机号收发，不便时使用自己已测通的号码；两种情况下管理员后台都须查看顾客回复、主动发出及回复短信。Apple 同账号条件适用于发短信的 iPhone 与执行转发的 Mac 用户，后台管理员身份与此无关。店主随后明确选择先换成女朋友的号码，并表示现有或新建用户均可；现已建立下述独立用户。设备已登录、用户确认号码验证成功，本地自动化检查通过；加拿大测试虽由工具报告已提交，收件人未收到且 Mac 最终显示未送达。回复数据库仍拒绝读取，尚未验收她的短信通道。

已只读检查现有 `imsg watch --help`，0.4.0 支持按会话、参与者和增量游标筛选；没有取得聊天内容、没有启动监听。用户已在系统界面授予读取权限，但实际检查仍被拒绝，接收还需有效的完全磁盘访问权限与真机反向回复测试。实际范围包括已选业务会话的收件、后台发件及手机直接回复同步，排除整库历史上传；完整设计和账号切换过渡见 [消息方案](../01_research/tech/STUDIO_MESSAGING_PLAN_20260911.md)。

## 女朋友号码切换：发送已尝试，实收未通过

2026-09-11 实际准备完成：

- Mac 电脑名称为 `chi的Mac mini`。原有用户 `chix`（501）和 `chix2`（502）保留；新建标准用户 `pindou_sms`，显示名称 `PinDou SMS`，UID 503，主目录 `/Users/pindou_sms`。已核对其不属于 admin 组。
- `sysadminctl` 创建目录服务用户后没有立即生成主目录；随后仅针对该新用户运行 `createhomedir -c -u pindou_sms`，主目录已生成。本地登录密码校验通过，没有重置原有用户密码。
- 在 `/Users/pindou_sms/Library/Application Support/PinDouSMS/` 安装原有测试脚本（目录 0700、脚本 0600、该用户所有）；以新用户身份运行默认工具检查通过，`imsg` 仍为 0.4.0。没有复制旧测试的收件人授权或发送日志，也没有发出新短信。
- 本地 Mac 密码只保存于 Mac 原用户私有的 `partner-user-setup.json` 和 Windows 忽略且限制 ACL 的 `artifacts/mac-sms/private/partner-login.txt`，不提交密码。该密码不是 Apple 账户密码。
- 后续实际检查发现 `pindou_sms` 已成为前台用户，`gui/503` 存在、“信息”App 已运行。店主确认手机上的号码验证已成功；配对的实际短信收发尚待验收，后台双向收发仍待实现。

店主操作：

1. 在 Mac 切换到 `PinDou SMS`（`pindou_sms`），使用私有文件中的本地登录密码。用快速用户切换或锁定屏幕后切换用户，保留现有工作会话。
2. 由她本人在新用户中登录自己的 Apple 账户并完成双重认证，打开“信息”App，确认其中的 Apple 账户与她的 iPhone 一致。
3. 在她的 iPhone「设置 → App → 信息 → 短信转发」开启 `chi的Mac mini`；若出现设备确认码，在 iPhone 中完成确认。
4. 完成后继续核对实际发信号码，再按获准的测试收件人进行双向测试；读取权限只在需要接收时按 macOS 系统提示处理。

这些步骤完成前，后续执行不得在旧 `chix` 用户下发短信并将其算作女朋友的通道。恢复准备时先读取已有的私有设置状态，避免重复建用户或重置其密码。

### 本轮实际测试与权限检查

- 经店主再次要求测试，在 `gui/503`、`pindou_sms` 身份下对原先获准的 +86 号码执行一次测试。工具在约 0.9 秒后退出 1，原始日志保留 `outcome_unknown`；店主确认没收到。没有重发该请求。
- 随后的只读 Apple Events 检查返回 `-1743`，即控制“信息”未获授权；信息数据库只读连接也不可用。只读取了权限诊断和数据库结构是否存在，未遍历聊天内容。
- 系统日志将 SSH 检查归因于 `com.apple.sshd-keygen-wrapper`。为通过本地 GUI 完成权限设置，新增 `mac_sms_permissions.py` 并用“终端”打开；日志确认为 `com.apple.Terminal`。本地检查仍报告自动化未允许、数据库不可读，需要用户在系统设置授予权限，不能用修改 TCC 数据库替代。
- 用户随后确认两项开关已打开。修正检查脚本的兼容问题：实际 macOS 15.6 的 `/System/Applications/Messages.app/Contents/Resources/Messages.sdef` 使用 `accounts`，旧 `count of services` 检查会等待超时，不能将其等同于用户未登录。改为 `count of accounts` 后本地自动化检查通过，返回 6 个账户对象；这不是 6 个独立 Apple 账户的结论。
- 店主另提供加拿大号码作为测试收件人，并通过截图明确女朋友的发信号码。它们仅保存于该用户私有的 `canada-test-20260911/test-recipient.json`。加拿大单条测试已在本地 Terminal 下执行，`imsg` 退出 0，原始状态记 `tool_reported_sent`。收件人随后确认没收到，Mac 会话显示红色叹号/未送达。用户重新开启 iPhone 短信转发后曾暂时不再显示红色报错，但仍未收到，随后又补充电脑发送失败。因此发送工具返回成功不能作为本次送达凭据，未自动重复调用该测试。
- 用户提供的手机手动测试为蓝色 `222`、显示 iMessage 已送达，只证明 iMessage 通道可用；不能据此证明该 SIM 的普通短信可以发出。用户新建信息、手动输入加拿大收件号码后仍显示 iMessage；改用获准的 +86 号码后显示绿色。应核对输入框的 SMS/RCS 标识，不能仅靠颜色判断；iMessage 路由不由双方是否存为联系人决定。[Apple 消息类型](https://support.apple.com/en-ca/104972)
- 经明确的手机端 SMS 测试指引，她向获准的 +86 号码发送 `123`，用户确认收到，发件人显示联系人名称。该结果证明手机直发这条短信已送达，尚未验证实际发件号码。随后用 `pindou_sms` 下本地 Terminal 对同一 +86 号码执行一个独立的 Mac 转发测试，目录 `china-relay-test-20260911`，请求 `partner_cn_relay_20260911_02`；原固定测试文案不变，工具退出 0、`tool_reported_sent`，但用户再次确认未收到。这次使用独立日志，没有重放原失败请求；未重复测试加拿大收件号码。
- 本地只读枚举账户连接状态，SMS 与 iMessage 均自报启用且 connected，RCS 为未启用、disconnected。其余 3 个对象未识别类型，不解释为额外 Apple 账号。账户状态本身不能证明短信转发成功；正在核对 Mac“信息”设置里实际选中的号码，以及失败测试是否同步出现在她的 iPhone 中。当前 imsg 0.4.0 源码选取首个 SMS 类型的服务并提交 AppleScript 发送，不提供运营商实收证明；没有凭退出 0 宣布成功。[imsg 0.4.0 发送实现](https://github.com/openclaw/imsg/blob/v0.4.0/Sources/IMsgCore/MessageSender.swift)
- 新 Mac 用户的系统 Apple 账户与手机截图给出的账户标识比对一致，仅输出匹配布尔值；没有将完整账户标识写入此文档。该比对不代替“信息”App 账户、SIM 线路与转发的逐项验证。
- 回复读取仍失败：数据库文件存在，但读取文件头返回 `EPERM`（1），Python SQLite 和系统 sqlite3 的只读结构查询均返回授权拒绝。只检查了文件头和数据库结构可读性，没有取得聊天正文。用户自述的已开启状态与实际访问结果尚不一致，需进一步核对有效授权。只读查询 Terminal 权限记录也被拒绝；没有修改 TCC 数据库。
- 已检查并只重开 `pindou_sms` 下的两个空闲测试 Terminal 实例（其子进程只有 login 和登录 shell）；`chix` 的 Terminal 和其他服务未操作。重开后自动化仍通过、回复文件读取仍被拒绝。
- 提供 `mac_sms_console_test.py`：先检查权限，再复用已有的幂等发送脚本。回复检查只统计选定收件人自测试开始后发来的指定标记，区分 SMS 与 iMessage；不输出其他短信内容。离线样本验证了号码、时间、方向、标记、正文编码及渠道隔离。
- `.command` 操作位于该用户 `~/Library/Application Support/PinDouSMS/`，包括 `1_check_permissions.command`、`2_send_test.command`、`3_check_reply.command`，以及独立的 `4_send_china_relay_test.command`。发送脚本支持限定在该目录内的测试子目录、加拿大或中国收件号码及对应回复标记；每个发送请求仍须具有私有授权配置且只尝试一次。已在 Mac 打开该目录；通过 SSH 写桌面会被其独立隐私权限拦截，因此工具保留在应用支持目录。
- 切换到 `pindou_sms` 后，`gui/501` 仍在，反代 8317 与 IB Gateway 4002 的 TCP 连接检查通过。这不代替交易连接、行情或长期共存验收。

当前下一步：核对 Mac“信息 → 设置 → iMessage”中的实际发信号码，以及最新 Mac 测试是否出现在她的 iPhone 对话中，排查 Mac 转发这段。她的 iPhone → +86 直发测试已由收件人确认收到，同一 +86 的 Mac 测试仍未收到；需核对显示联系人名背后的实际发件号码。加拿大号码的蓝色 iMessage 不作为普通短信测试通过。并核对 `pindou_sms` 中 Terminal 的有效完全磁盘授权，确保实际只读检查通过。之后再验证指定标记回复回传及切回 `chix` 后共存。各次测试日志分别保留，不能把未收到的请求直接自动重放为“重试成功”。

## 设备与单条测试步骤

1. 店主在 Mac 的“信息”App 确认同一 Apple 账号，在 iPhone「设置 → App → 信息 → 短信转发」启用该 Mac；若 macOS 请求控制“信息”的自动化权限，由店主在系统界面确认，不修改 TCC 数据库。
2. 店主提供另一个获准接收一条测试短信的 +1 或 +86 号码，确认固定文案：`小狗拼豆铺短信测试，无需回复，不会创建预约。`
3. 仅收到上述明确授权后，才在 Mac 私有目录创建 `test-recipient.json`（0600），包含 `recipient`、随机 `request_id`、`approved_at` Unix 时间与完全一致的 `approved_text`。不将号码写入 Git 或公开日志。
4. 运行已准备的测试脚本一次。发送请求在本地 SQLite 日志先落 `started` 再调用工具；返回成功仅记 `tool_reported_sent`，最终送达及发出号码由收件人核对。错误或超时记不确定，不自动重发或切换渠道。
5. 核对实际是 CTExcel 卡发出的短信，而非误走 iMessage、其他 SIM 或 Apple 邮箱。Mac 与 iPhone 任一离线时不能宣称链路可用。

工具基本检查：

```sh
/usr/bin/python3 "$HOME/Library/Application Support/PinDouSMS/mac_sms_probe.py"
```

完成授权文件后，单条测试：

```sh
/usr/bin/python3 "$HOME/Library/Application Support/PinDouSMS/mac_sms_probe.py" --send-approved-test
```

`test-recipient.json` 是仅供这次明确许可的测试输入。它不是服务端可随意修改的群发名单。真实业务发送还需要已验证通知联系方式、偏好、业务事件队列、过期处理、手机/Mac 可达状态及发送记录。

## 当前边界

- CTExcel 官网页面说明套餐包含全球短信；具体个人套餐和自动业务用途仍待核验。单条测试成功不代表经营用途已经获得运营商认可或漫游费用已经确认。
- `imsg` 0.4.0 的退出成功不作为运营商送达凭据；较新文档的全部结果分类不能直接算作这个已安装旧版本的功能。
- 多号码 Apple 账号的发出号码选择需要真机确认。后续生产桥接优先由 Mac 主动领取经认证的发送任务，不将当前通用 SSH 权限暴露给网站用户。
- 本阶段只测试短信发送。接收回复、获取聊天历史及自动代回复均不是本次已完成的能力。

参考：[Apple 短信转发](https://support.apple.com/en-ie/102545)、[imsg 发送](https://imsg.sh/send.html)、[CTExcel 官方介绍](https://www.ctexcel.ca/aboutus.jspx)。
