# 顾客预约英文通知遗漏修正：发布与验收

日期：2026-09-24（America/Toronto）。生产：`36.139.201.94`。

## 原因与范围

店主收到 11:04 的 `Booking request received` 邮件，正文仍是旧短版，且含中文顾客称呼。线上通知记录显示当日 15:04:51 UTC 新接受了一条 `pending` 邮件；旧版 `delivery_payload` 仅为 `confirmed` 的短信／邮件选择完整模板，`pending`、`cancelled`、`reminder` 仍取旧英文正文。前次发布文档对“全部提醒”覆盖范围的描述过宽，已标记修正。

四类预约状态的短信／邮件现都包含预约时间、人数正确单复数、Hamilton 当地时间、店址、预约链接和店铺详情链接。短信提示直接回复，邮件提供 `staywithcsq@outlook.com`。待确认邮件明确等待店主确认，不误写为预约成功。英文投递遇到非 ASCII 称呼时以 `Hello` 称呼；数据库、店主记录和原始顾客姓名不改。已尝试投递任务保留原有效负载及幂等键；未尝试投递的旧任务在发送前重建。已送达的旧邮件不能追改，本次没有自动重发。

微信订阅消息的数据字段维持英文，人数一人／多人文法已修正；微信平台固定模板标题由平台配置决定，本次短信／邮件修正未更换平台模板。

## 验证

- 通知、短信桥及微信相关测试共 43 项通过；文案审批校验、Vue 类型检查和生产构建通过。
- 生产发布前为 `20260924023755-studio-v7`，417 文件清单全部有效。新包以线上清单为底，只替换 `service/customer_notifications.py` 与 `service/customer-notification-copy.json`，其余 415 文件复用；没有发布工作区的其他产品代码。
- 首次修正为 `20260924151611-studio-v7`；专项测试随后发现微信英文人数提示受 20 字符上限截断，于是仅替换文案文件，最终版本为 `20260924152310-studio-v7`。两个版本各自的 417 文件哈希有效；最终公网 `/studio-api/health` 返回 `ok`，Studio 与生成器服务 active。每次发布前后的 Studio、生成器业务表和受保护成员／账本摘要逐项相同。
- 在最终生产服务运行环境中用虚构的中文称呼、单人预约验证 `pending`、`confirmed`、`cancelled`、`reminder` 各自的邮件与短信正文，共 8 种组合均通过英文、时间、人数、店址、两条网址及联系方法断言；微信英文人数提示也按真实字段长度验证。未调用真实短信或邮件服务商；真实设备送达不由此测试证明。

## 回退与证据

最初版本：`/opt/pindou/studio/releases/20260924023755-studio-v7`；最终版本的前一版：`/opt/pindou/studio/releases/20260924151611-studio-v7`。备份分别为 `/opt/pindou/studio/backups/20260924151611-studio-v7`、`/opt/pindou/studio/backups/20260924152310-studio-v7`。如需回退，须先核对新机最新数据库和通知投递状态，不可直接恢复旧队列快照导致重复发送。此版本只修改通知代码和文案，没有数据结构变更。

本机审计：`artifacts/studio-release/before-notification-correction.json`、`after-notification-correction.json`、`before-notification-followup.json`、`after-notification-followup.json`；最终包元数据：`latest.json`。这些文件均在 Git 忽略目录。生产凭据、顾客记录及完整备份未提交 GitHub。
