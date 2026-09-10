# Telegram 店主预约提醒

来源：2026-09-10，店主确认 Server 酱微信提醒已经收到，但服务号折叠后不醒目；同意继续接入 Telegram 主提醒，保留微信独立发送。

## 已实现

- 预约提交和顾客自行取消，在同一个业务事务中为已经启用的渠道分别创建任务。两个渠道有独立发送 worker、配额和重试时间；一个服务连接失败不阻塞另一个。
- 新增 Telegram 管理抽屉：保存机器人 Token、中文／英文、接收人绑定及更换、启停、测试和最近 30 条记录。原 Server 酱入口、配置及密钥继续保留。
- Telegram 消息直接展示称呼、日期、起止时间、人数和预约编号，带打开店主工作台的按钮。不发送联系方式、留言或私密备注。使用 HTML 转义、关闭链接预览，普通非静音消息；手机最终响铃和显示仍受 Telegram／系统通知设置控制。
- 后台保存 Token 时调用 `getMe` 验证机器人，并检查 `getWebhookInfo`。发现其他 webhook 时拒绝接管，不调用 deleteWebhook，不删除已有更新。
- 绑定：后台生成一个随机链接；接收人打开 `t.me/<bot>?start=<challenge>` 并按 Start。只接受匹配临时凭据、私聊、本人 sender/chat ID 一致的消息；不能通过任意用户先发 /start 抢占收件人。
- 链接 10 分钟有效，只保存凭据哈希；新链接使旧链接失效。绑定检查要求完整管理员权限，配置版本保护，检查期间使用有限 getUpdates 长轮询。平时不抓取或保存 Telegram 聊天消息。
- 绑定成功后开启提醒并发一条测试，不创建顾客预约。更换收件人后，尚未发送的旧收件人任务停止发送；换机器人后必须重新绑定。相同机器人 Token 更新／恢复可以保留收件人。

## 安全与维护

- Token 仅写入 `/opt/pindou/studio/shared/telegram-secret.json`，0600、pindou 用户所有。API、日志及 Git 不回传密钥；前端保存／关闭后清空输入。
- 仅调用固定 `https://api.telegram.org` 下的允许方法，拒绝重定向。不在错误日志打印包含 Token 的请求 URL 或原始错误描述。
- 429 使用 Telegram 提供的 retry_after，403 提示解除屏蔽，401/404 提示更新 Token；其他临时失败按发送队列退避。每条任务最多 8 次，超过 24 小时停止发送；服务重启可恢复。
- 保护阈值按渠道隔离：Telegram 每秒单聊不超过一次、每分钟最多 30 次、滚动一天最多 10,000 次；Server 酱仍按账号设置 5/1,000 次。没有为 Telegram 开启付费广播。
- Telegram 的 API 接受表示消息已创建，不表示接收者已经阅读。网络响应丢失或提交结果前进程中断仍可能导致罕见重复，不宣称跨平台 exactly-once。
- 新增 `studio_telegram_settings`、`studio_telegram_bindings`；原通知表增加 channel/target，原请求计数增加 channel，已有记录默认属于 Server 酱。

## 接口

全部要求店主管理员权限：

- GET/PUT `/studio-api/manage/telegram-notifications`
- POST `/studio-api/manage/telegram-notifications/bind`
- POST `/studio-api/manage/telegram-notifications/bind/check`
- POST `/studio-api/manage/telegram-notifications/test`
- POST `/studio-api/manage/telegram-notifications/{id}/retry`

## 本地验收

- 253 项完整后端测试通过。随后补充同一机器人 Token 丢失后的恢复条件，最终 Telegram 专项 19 项通过；原 Server 酱 19 项回归通过。
- Chromium 320/390/768/1440/2560 与 WebKit 390/1440，两种语言共 14 个状态：机器人验证、临时链接绑定、首次测试、再次测试、密钥清空及微信配置保留均通过。
- 页面无错误，无横向溢出，输入框未被裁切；抽屉 axe 无违规。
- 构建和 68 模块文案检查通过；仅新增 telegram-notifications 文案模块。模拟提供商与隔离数据库不能代替真实 Telegram 收件验证。

## 发布与待完成事项

已发布 `20260910171839-studio-v7`（build `2026-09-10T17:12:13.783Z`），365 个文件，归档 SHA-256 `6caeafcc7533d975bf8cce086a479638460ff76c8ba0dac283a0418e42bb2c20`。

线上文件全量校验通过，健康检查 200，未登录访问 Telegram 管理接口为 401。既有业务表与发布前备份一致；Server 酱密钥文件哈希、启用状态、语言、配额和配置版本均保持，原生成器发布目录保持。验证记录位于 `artifacts/telegram/`。

Telegram 实时扫码登录窗口已打开，仍待店主登录。机器人账号、品牌名称头像、实际 Token、实际接收人以及真实收件测试尚未完成；未配置时 Telegram 默认关闭，不补发历史预约。微信现有通知保持启用。

参考：[Telegram 官方创建机器人教程](https://core.telegram.org/bots/tutorial)、[Bot API](https://core.telegram.org/bots/api)、[Start 绑定链接](https://core.telegram.org/bots/features#deep-linking)。
