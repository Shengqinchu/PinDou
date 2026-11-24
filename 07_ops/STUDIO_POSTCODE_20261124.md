# 地址邮编改为 L8R 0A9（2026-11-24）

店主在详情页地址截图中圈出“ON L8R 0B1”，标注“改成L8R0A9”。

## 改动

- 公开地址 `8 Hughson St N, Hamilton, ON L8R 0B1` → `8 Hughson St N, Hamilton, ON L8R 0A9`（按原格式保留空格）。
- 地址有三处来源，全部更新：`studio-profile.json`（网站、后端顾客通知用的 `service/studio-profile.json`）、`contact-fields.address` 中英文（网站与小程序）、`06_studio/content-defaults.json` 中同一条。测试断言同步。
- `studio_frontend_pack.py` 允许按名称发布 `studio-profile.json`（该文件本就在线上 manifest 中，原来只能整包发布时更新）。
- 线上已发布覆盖 `studio_content['contact-fields']`：1/0 → 2/2，只含 `address`；actor `owner-request:claude-20261124`。小程序 0.1.34 包内仍是旧邮编，靠这条覆盖显示新邮编，无需重新提审。若之后在后台“网站编辑”保存 contact-fields，与默认值相同的地址会被压缩掉，小程序会回落到包内旧邮编，直到下个小程序版本。
- 已发出的短信、通知与会话历史中的旧邮编原样保留；改动时没有待发送的提醒含旧邮编。

## 发布与验证

- `test_customer_notifications.py` 17 项通过；`npm run build`（含文案检查）通过，产物中无旧邮编。
- 以 `20261114022614-studio-v7` 为基准发布 `20261124193941-studio-v7`（55 个前端文件 + `content-defaults.json` + `studio-profile.json`，2151 个文件哈希有效），服务 active。
- 发布前后两库业务数据指纹一致；`/studio-api/content` 返回新地址；`/details`、`/visit`、首页、小店、健康检查 200；`/details` 桌面截图显示 “8 Hughson St N, Hamilton, ON L8R 0A9”。小程序真机未打开核对。

回退版本 `/opt/pindou/studio/releases/20261114022614-studio-v7`，自动备份（含改覆盖前的整库）`/opt/pindou/studio/backups/20261124193941-studio-v7`。
