# CTExcel / iPhone / Mac 短信测试准备

2026-09-11。店主确认 CTExcel 主卡继续在日常 iPhone 中，并有可长期开机、使用同一 Apple 账号的 Mac。按 [消息方案](../01_research/tech/STUDIO_MESSAGING_PLAN_20260911.md) 继续准备；目前只进行单条短信测试的设备准备，不代表预约短信已上线。

## 已完成

- 通过既有 `macmini` SSH 配置实际连通 Mac mini：macOS 15.6、arm64、当前桌面用户 chix。
- 已安装 `/opt/homebrew/bin/imsg` 0.4.0；`send --help` 确认支持 `--service sms`、E.164 收件人、JSON 输出。保留原有工具版本，没有升级全局 Homebrew 工具或修改其他服务。
- 新增 `07_ops/mac_sms_probe.py`，复制到 Mac 的 `~/Library/Application Support/PinDouSMS/mac_sms_probe.py`；目录 0700，脚本 0600。默认只检查工具，只有显式 `--send-approved-test` 才可能调用发送。
- 检查工具可执行通过。7 项离线测试通过：授权文案/时间/号码校验、SMS 路由、结果脱敏、重复请求、超时及进程中断后不重发。离线收件人是虚构号码、发送程序为模拟。
- 已打开 Mac 的“信息”App，供店主确认 Apple 账号和设备设置。未读取聊天记录或联系人。
- 发起过一次只读 AppleScript 服务数量检查，18 秒未返回而终止；只能记录为“等待 macOS 权限或应用响应”，不能据此宣称已经授权、未登录或短信转发已开启。

本轮没有发送真实短信、没有创建或更改顾客预约、没有安装自动启动发送服务，也没有开放 Mac 的公共发送端口。

## 设备与单条测试待完成

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
