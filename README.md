# PinDou — AI 拼豆图纸生成 SaaS

专攻人像 / 宠物 / 情侣照的 AI 拼豆图纸生成器。微信小程序优先，Web 端预埋。

## 当前阶段
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

## 角色
- 用户：产品负责人，最终拍板
- chat 端 Claude：架构顾问 / 评审
- Claude Code：项目协调 + 文档版本控制 + 派单
- Codex：后端 + 调研执行
- Gemini：前端 + 设计（Phase 2 启用）
