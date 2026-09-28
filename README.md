# PinDou — AI 拼豆图纸生成 SaaS

> **当前运维入口（2026-09-18）**：小狗拼豆铺网站、小程序后端及原图纸服务已完整迁至移动云 `36.139.201.94`（8核 / 16GB / 80GB / 8Mbps），到期 **2027-09-18**。后续运维统一使用新机。详见 [服务器资产与密钥位置](07_ops/SERVER_ASSETS.md)、[当前部署说明](07_ops/deployment.md)、[迁移验收](07_ops/PINDOU_FULL_MIGRATION_ACCEPTANCE_20260918.md)。当前 Studio 开发/运维分支为 `codex/studio-v1-20260907`。

专攻人像 / 宠物 / 情侣照的 AI 拼豆图纸生成器。微信小程序优先，Web 端预埋。

## 初始阶段记录
**Phase 0 — 调研立项**（2026-05-24 启动）

## 目录导览
- `00_meta/` — 项目元信息（章程、决策日志、路线图、Skills/API 盘点、周报）
- `01_research/` — Phase 0 调研产出（技术 / 竞品 / 用户 / 色卡 / 合规 / 市场）
- `02_product/` — PRD / 定价 / 功能规格（Phase 1+）
- `03_design/` — 设计系统 / 线框（Phase 2+，Gemini）
- `04_architecture/` — 系统设计、API spec、数据模型、ADR
- `05_frontend/` — 小程序与 Web 前端（Phase 2+，Gemini）
- `06_backend/` — 后端服务（Phase 2+，Codex）
- `07_ops/` — 部署 / 监控 / 安全
- `08_growth/` — 增长 / 小红书运营

## 关键决策入口
- 项目章程：`00_meta/PROJECT_CHARTER.md`
- 决策日志：`00_meta/DECISION_LOG.md` + `04_architecture/ADRs/`
- Phase 0 综合简报（产出中）：`00_meta/phase0_summary.md`

## 手作业务知识

- [知识总索引](01_research/KNOWLEDGE_INDEX.md)：查找拼豆与后续手作业务资料。
- [拼豆知识库](01_research/colormap/INDEX.md)：色卡、品牌、供应链与领域知识。
- [布贴热压知识库](01_research/patches/INDEX.md)：现成布贴定制帆布包/衣服的材料、设备、工艺、采购、成本与试样 SOP。2026-09-27 完成首轮文献调研，具体材料效果仍待实测。

## 角色
- 用户：产品负责人，最终拍板
- chat 端 Claude：架构顾问 / 评审
- Claude Code：项目协调 + 文档版本控制 + 派单
- Codex：后端 + 调研执行
- Gemini：前端 + 设计（Phase 2 启用）
