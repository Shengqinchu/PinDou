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
