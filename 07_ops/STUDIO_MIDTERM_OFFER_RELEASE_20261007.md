# 预约页活动上新：期中特惠（2026-10-07）

店主截图标注：“更改优惠：期中特惠 至11.11 / 单板不限时（52钉） 29.9 / 四人同行，一人免单”。

## 改动

- 预约页右下活动卡片沿用原双节特惠的三个 `visit-flow` 键（键名不变）：`holiday_offer_title`“期中特惠 至11.11 / Midterm offer · until November 11”，`holiday_new_guests`“单板不限时（52钉） CAD 29.9 / One 52-peg board, no time limit · CAD 29.9”，`holiday_bring_friends`“四人同行，一人免单 / Groups of four: one guest free”。储值 CAD 7／小时与布贴试营业特惠不变；不改预约时长、结算、积分或布贴赠送规则。提交 `bd02def`；授权记录、目录与批准哈希同步。
- 小程序（0.1.29 线上、0.1.30 审核中）运行时读取 `/studio-api/content` 中同键的已发布内容，因此通过后台内容发布同一逻辑写入 `studio_content['visit-flow']`（version/published_version 1/0 → 2/2，history 记录 actor `owner-request:claude-20261007`），先于新默认值上线，保证三键作为显式覆盖存在。注意：若之后在后台“网站编辑”保存 visit-flow，与新默认值相同的键会被压缩掉，届时小程序会回落到包内旧文案，直到下一版小程序打包新文案。

## 验证与发布

- 文案契约、类型检查、构建通过；本地 QA 中英文、1440/390 宽度截图核对，无溢出与页面错误。
- 发布前核对线上 `content-defaults.json` 与 GitHub 基线 `ef02468` 一致。以 `20261002224110-studio-v7` 为基准发布 `20261008003849-studio-v7`（55 个前端文件 + `content-defaults.json`）；1312 个文件哈希有效，两库业务数据指纹前后一致，服务 active。
- 公网：`/studio-api/content` 返回三条新文案；`/visit` 中英文桌面及手机显示新活动，布贴试营业特惠（剩余 7/10）照常显示，无页面错误；首页、小店、健康检查 200。小程序真机未打开核对。

回退版本 `/opt/pindou/studio/releases/20261002224110-studio-v7`，自动备份 `/opt/pindou/studio/backups/20261008003849-studio-v7`；内容可在后台“网站编辑”历史中回看。
