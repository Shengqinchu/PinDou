# Questions For User

## 2026-05-24 — Task C API PoC follow-up

已处理：

- P1 `gpt-image-2` key 已通过本地 `.env` 补齐。
- P1 真实 API 已跑通 40/40 样本，结果见 `01_research/tech/poc_results.csv`。
- 量化输出图已生成，投票模板见 `01_research/tech/subjective_vote_template.csv`。

用户问题处理结论：

1. Q1 已解决：`.env` 已有 P1 key，P1 `gpt-image-2` 已跑通。
2. Q2 已确认：火山即梦 / 阿里通义万相本阶段跳过，P2/P3 留作 Phase 2 备选 provider 评估。
3. Q3 已确认：5 人主观投票由用户线下组织；Codex 只交付 `subjective_vote_template.csv` + `poc_samples/` 完整图集，投票数据回来后再汇总平均分与通过率。

## 2026-05-24 — Task H schema / Phase 1 PRD handoff

需要用户 / Claude 在 Phase 1 PRD 阶段确认：

1. 价格 schema 是否拆出独立 SKU 表？Task H 已出现 CNY / USD / EUR 混合价格样本，继续放在 `price_per_1000pcs` 会丢失币种、包装规格、平台和采集时间。建议 Phase 1 新增 `bead_skus`：`brand + bead_diameter_mm + code + platform + currency + pack_count + price + captured_at`。
2. `stock_status` 是否允许 `unknown` / `unverified`？公开源经常只能确认“色号体系存在”，不能确认某个豆径当前在售。当前 Task H 为了不改 schema，仍用 `common/rare` 并在 `notes` 里说明置信度。
3. Phase 1 PRD 衔接建议：`PatternBuilder.build(preview, size, brand, bead_diameter)` 先只开放 `MARD 5mm` 作为默认生产路径；后台可读取 Task H 的全库做隐藏实验，但 UI 不要让用户切 Hama/Perler/Artkal，直到 SKU 表、币种和实物色卡校准完成。

## 2026-05-24 — Task I China deep-dive PRD impact

给用户 / Claude 的 Phase 1 PRD 建议：

1. 默认色卡仍建议先用 MARD，但不要只写“MARD 5mm”。国内公开 SKU 和工具语境明显偏 `MARD/COCO/黄豆豆/DODO 2.6mm 小豆`，建议 Phase 1 默认文案改成“入门默认 MARD 5mm；人像/宠物隐藏实验 MARD 2.6mm”。
2. Task H 缺 `漫漫 / ManMan` 独立色卡。中文工具（拼豆星球、德虎、metamo）常见五件套是 MARD / COCO / 漫漫 / 盼盼 / 咪小窝，Phase 1 前建议补 `manman_*` 或确认映射。
3. Schema 建议新增：`bead_skus`（平台 SKU 表）、`china_market_status`（active / low_stock / discontinued_cn / new_release / unknown）、`aliases_cn`（中文别名）、`source_confidence`（每字段置信度）。不要把这些硬塞进现有 palette row。
4. 小红书 ≥200 篇完整样本需要用户 App 内人工补采；Codex 已交付 `xhs_manual_collection_template.csv`。未登录公开 Web 只适合入口和少量卡片线索，不应为凑量绕平台限制。
5. UI 色号搜索建议支持“奶白、腮红粉、描边黑、透色、黑白补充包”等中文口语词；材料清单仍显示品牌官方 code，别名只作为辅助搜索/展示。

## 2026-05-24 — Phase 2 backend task 0 review

任务 0 已完成服务器硬件盘点与低风险安全加固，结论给用户 / Claude review：

1. 上海生产机实测为 Ubuntu 22.04.5 LTS，8 vCPU，15 GiB RAM，系统盘 80G；`/dev/sda1` 与 `/var` 同盘。旧服务清理后当前约 79G total / 6.9G used / 69G available。
2. 硬盘低于 brief 的 100GB 阈值。当前已释放约 15G，MVP 短期可继续开发；上线前仍建议二选一：A. 接对象存储（OSS/COS/七牛）；B. 扩容到 ≥200GB 再允许用户原图/Preview 长期落本地盘。
3. 已完成 SSH key 认证：本地 `.env` 已切到 `PINDOU_PROD_SSH_USER=pindou` + `PINDOU_PROD_SSH_KEY_PATH`，旧 `PINDOU_PROD_SSH_PASS` 已移除；服务器已禁用密码登录，root 仅保留 key 登录应急。
4. 已创建 `pindou` 部署用户，启用 fail2ban，并启用 UFW：公网入站只允许 `22/80/443`。
5. 旧服务清理：已停用并移除 `claude-shop`、`cloudflared`、Docker `wxhm/new-api`、旧 Nginx 站点、`rpcbind`；已删除 `/opt/claude-shop`、`/root/new-api-data`、`/root/apisell`、`/root/wxhm-data`、`/var/lib/docker`、旧静态站点和缓存日志。
6. 当前端口：公网仅 SSH `22` 在监听；`80/443` 在 UFW 预放行但 Nginx 当前 inactive，等 PinDou 部署时重新启用。另有 `127.0.0.1:31088` 云探针，仅本机监听。

## 2026-05-25 — Phase 2 backend task 1 review

任务 1 已完成后端骨架与本地验证，结论给用户 / Claude review：

1. 已创建 `06_backend/` FastAPI 项目骨架，包含 `pyproject.toml`、`requirements.txt`、后端 `.env.example`、`pindou/` 包结构和 `tests/`。
2. 已按 PRD §5 保留 `PreviewProvider.generate(...)`、`PatternBuilder.build(...)`、`PatternSheet`、`ColorRef` 等契约轮廓；本任务只做占位，不实现业务逻辑，不改字段名。
3. 已用 `pydantic-settings` 实现配置加载，读取根目录 `.env` + `06_backend/.env`，密钥字段使用 `SecretStr`，没有把 key 写进 commit。
4. 本地 `.venv` 已安装核心依赖；`pytest` 通过；`uvicorn pindou.main:app --host 127.0.0.1 --port 8000` 已验证 `/health` 返回 `{"status":"ok"}`。
5. 服务器 UFW 已重新执行放行并启用：`22/80/443` allow，`ufw status verbose` 为 active；实际监听仍只有公网 SSH 与本地云探针。
6. 待 review 后进入任务 2：实现 `XiaochiGptProvider` + fallback chain，并开始接 PRD §5.1 的真实 PreviewProvider。

## 2026-05-25 — Phase 2 backend task 2 review

任务 2 已完成 PreviewProvider 实现，结论给用户 / Claude review：

1. `StylePreset` 已按 Gemini 前端 `05_frontend/api/index.ts` 对齐为 `q_portrait` / `q_pet` / `q_couple` / `cartoon_fallback`；`SizePreset` 保持 `60x80` / `80x100` / `100x120`。
2. 已实现 `XiaochiGptProvider`：通过 openai SDK 调反代 `gpt-image-2`，单次 90 秒超时，失败重试 1 次，第二次带不同 seed hint；prompt 采用 Task C 的 Q 版拼豆约束，重点限制“不补腿脚 / 不补身体 / 不加额外物体 / 去水印和背景杂物”。
3. 已实现 `PreviewProviderChain`：主 provider 失败后走 backup，最后走 `FallbackProvider`；chain 会累计 `fallback_count` 并记录失败 provider。
4. 已实现 `FallbackProvider`：调用 `PatternBuilder.build(raw_image=...)`，并把 `PatternSheet.grid` 渲染为 PNG preview。注意：真实 `PatternBuilder` 仍在任务 3 实现，本任务测试里用 fake builder 验证 fallback 逻辑。
5. 已实现 ADR-007 反代健康检查：FastAPI lifespan 启动后台 monitor，每 `REVERSE_PROXY_CHECK_INTERVAL_SECONDS` 检查 `REVERSE_PROXY_HEALTH_URL`，连续 3 次失败且累计超过 `REVERSE_PROXY_ALERT_AFTER_SECONDS`（默认 21600 秒 / 6 小时）写 error 日志告警。
6. 已补测试：mock OpenAI 调用验证重试；验证 primary success、backup success、quantize fallback 三条路径；验证 ADR-007 三次失败触发告警。`pytest` 通过 7/7。

需要 Claude / 用户确认的接口衔接点：

1. PRD §5.1 原始 `PreviewResult` 写的是 `image: bytes`，Gemini 前端类型写的是 `preview_id + image_url`。当前实现兼容两边：provider 内部保留 `image` bytes，`to_frontend_dict()` 只输出前端 7 个字段。任务 5 API 落地时建议保存 PNG 到 `PINDOU_PREVIEW_DIR`，再返回真实 `image_url`。
2. `cost_estimate` 目前为 `0.0`，因为反代实际计费单价未进入配置。若产品页要展示成本或后台要统计毛利，建议任务 5/7 增加 `XIAOCHI_GPT_IMAGE_COST_CNY` 配置项。
