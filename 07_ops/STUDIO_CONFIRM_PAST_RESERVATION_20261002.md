# 店主可确认开始时间已过的预约（2026-10-02）

店主截图：`VIS-4F1563D29D0E4CB6`（10 月 2 日 17:30–20:00，待确认）在开始后保存“已确认”报 `reservation_in_past`，要求“时间过没过期都可以确认”。

- 后台确认（`PATCH /studio-api/manage/reservations/{id}` 状态改为 confirmed）及后台修改预约时间（`reservation_edits.validate_admin_change`）调用 `validate_interval(..., allow_past=True)`：跳过“开始时间已过”和“日期早于今天”；营业时间、时长、人数上限、14 天上限及与已确认预约冲突检查保留。顾客新建预约与顾客自助改期不变。提交 `ba89cd6`、`5f00c88`。
- 预约相关 107 项测试通过（含新增回归测试）；后端全量另有 `test_default_profile_names::test_custom_names_are_not_rewritten` 在修改前即失败，与本次无关。
- 发布前核对线上 `reservations.py`、`reservation_edits.py` 与 GitHub 基线 `7f108ab` 内容一致（线上仅换行符为 CRLF）。以 `20261002214739-studio-v7` 为基准发布 `20261002224110-studio-v7`：两个服务文件 + 57 个前端重建文件；1259 个文件哈希有效，两库业务数据指纹前后一致，公网 200。
- 线上只读验证：该预约按顾客规则仍为 `reservation_in_past`，按后台确认规则通过，容量无冲突。未代店主确认（确认会通知顾客）。

回退版本 `/opt/pindou/studio/releases/20261002214739-studio-v7`，自动备份 `/opt/pindou/studio/backups/20261002224110-studio-v7`。
