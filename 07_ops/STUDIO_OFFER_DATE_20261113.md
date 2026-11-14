# 期中特惠延期至 12.1（2026-11-13）

店主在预约页活动卡片截图中框出“至11.11”并标注“12.1”：“这里改一下时间”。

## 改动

- `visit-flow.holiday_offer_title`：“期中特惠 至11.11 / Midterm offer · until November 11” → “期中特惠 至12.1 / Midterm offer · until December 1”。活动内容（单板不限时 52 钉 CAD 29.9、四人同行一人免单）、储值优惠和其余文案不变；不改预约、结算、积分或布贴规则。
- 代码：`visit-flow.json`、`06_studio/content-defaults.json`（只改这一条；用 `prepare-content-defaults.py` 重新生成会顺带改动大量其他模块，所以没有用）、批准哈希、目录与授权记录。
- 线上已发布覆盖 `studio_content['visit-flow']`：版本 2/2 → 3/3，只换标题，另外两条覆盖保留为显式值；历史记录 actor `owner-request:claude-20261113`。小程序读取这份已发布内容，无需重新提审。注意：若之后在后台“网站编辑”保存 visit-flow，与默认值相同的键会被压缩掉，小程序会回落到包内旧文案（0.1.34 包内仍是“至11.11”）。

## 发布与验证

- `npm run build`（含文案检查）通过。以 `20261021235529-studio-v7` 为基准发布 `20261114022614-studio-v7`（55 个前端文件 + `content-defaults.json`，2098 个文件哈希有效），服务 active。
- 发布前后两库业务数据指纹一致；`/studio-api/content` 返回新标题；`/visit`、首页、小店、健康检查 200；`/visit` 桌面截图显示“期中特惠 … 至12.1”。小程序真机未打开核对。

回退版本 `/opt/pindou/studio/releases/20261021235529-studio-v7`，自动备份（含改覆盖前的整库）`/opt/pindou/studio/backups/20261114022614-studio-v7`；内容可在后台“网站编辑”历史中回看。
