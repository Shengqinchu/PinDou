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

店主最新要求优先使用女朋友的手机号收发，不便时使用自己已测通的号码；两种情况下管理员后台都须查看顾客回复、主动发出及回复短信。Apple 同账号条件适用于发短信的 iPhone 与执行转发的 Mac 用户，后台管理员身份与此无关。店主随后明确选择先换成女朋友的号码，并表示现有或新建用户均可；现已建立下述独立用户，等待她本人登录 Apple 账户与配对。

已只读检查现有 `imsg watch --help`，0.4.0 支持按会话、参与者和增量游标筛选；未读取信息库、未新增读取权限、未启动监听。接收还需设备上的完全磁盘访问权限与真机反向回复测试。实际范围包括已选业务会话的收件、后台发件及手机直接回复同步，排除整库历史上传；完整设计和账号切换过渡见 [消息方案](../01_research/tech/STUDIO_MESSAGING_PLAN_20260911.md)。

## 女朋友号码切换准备：等待 Apple 登录

2026-09-11 实际准备完成：

- Mac 电脑名称为 `chi的Mac mini`。原有用户 `chix`（501）和 `chix2`（502）保留；新建标准用户 `pindou_sms`，显示名称 `PinDou SMS`，UID 503，主目录 `/Users/pindou_sms`。已核对其不属于 admin 组。
- `sysadminctl` 创建目录服务用户后没有立即生成主目录；随后仅针对该新用户运行 `createhomedir -c -u pindou_sms`，主目录已生成。本地登录密码校验通过，没有重置原有用户密码。
- 在 `/Users/pindou_sms/Library/Application Support/PinDouSMS/` 安装原有测试脚本（目录 0700、脚本 0600、该用户所有）；以新用户身份运行默认工具检查通过，`imsg` 仍为 0.4.0。没有复制旧测试的收件人授权或发送日志，也没有发出新短信。
- 本地 Mac 密码只保存于 Mac 原用户私有的 `partner-user-setup.json` 和 Windows 忽略且限制 ACL 的 `artifacts/mac-sms/private/partner-login.txt`，不提交密码。该密码不是 Apple 账户密码。
- Apple 账户尚未登录、她的 iPhone 尚未配对，当前不能宣称已切换发信号码；后台双向收发仍待实现。

店主操作：

1. 在 Mac 切换到 `PinDou SMS`（`pindou_sms`），使用私有文件中的本地登录密码。用快速用户切换或锁定屏幕后切换用户，保留现有工作会话。
2. 由她本人在新用户中登录自己的 Apple 账户并完成双重认证，打开“信息”App，确认其中的 Apple 账户与她的 iPhone 一致。
3. 在她的 iPhone「设置 → App → 信息 → 短信转发」开启 `chi的Mac mini`；若出现设备确认码，在 iPhone 中完成确认。
4. 完成后继续核对实际发信号码，再按获准的测试收件人进行双向测试；读取权限只在需要接收时按 macOS 系统提示处理。

这些步骤完成前，后续执行不得在旧 `chix` 用户下发短信并将其算作女朋友的通道。恢复准备时先读取已有的私有设置状态，避免重复建用户或重置其密码。

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
