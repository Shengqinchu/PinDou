# Skills 盘点

> **范围**：当前 Claude Code 环境中可用的 skill；以及 Phase 0 任务里需要 Codex 去 GitHub 搜索补充的 skill 候选。
> **盘点日期**：2026-05-24
> **盘点人**：Claude Code

## 一、本地已加载的 Skills（系统当前会话内可调用）

### A. 本项目可用（必用 / 备选）

| Skill | 用途 | 本项目可用性 | 触发时机 |
|-------|------|------------|----------|
| `update-config` | 配置 Claude Code harness（settings.json、hooks、权限） | **备选** | 需要为 PinDou 配置自动 hook（如自动 commit、自动 test）时 |
| `fewer-permission-prompts` | 扫描 transcript 自动补 allowlist 减少权限弹窗 | **备选** | Codex/Claude Code 反复确认同类命令时使用 |
| `loop` | 设置定时循环任务 | **备选** | Phase 3+ 监控转化率 / API 余额时可能用 |
| `claude-api` | Claude API / Anthropic SDK 开发与迁移 | **必用（Phase 2+）** | 后端调用 Claude 做图片审核 / 用户文案生成时 |
| `simplify` | 审查改动代码、找复用与质量问题 | **必用（Phase 2+）** | 后端 / 前端 PR 自审 |
| `init` | 初始化 CLAUDE.md | **必用（Phase 1）** | 给 `06_backend/` 和 `05_frontend/` 各生成一份 CLAUDE.md |
| `review` | 审 PR | **必用（全阶段）** | 每次 Codex/Gemini 提 PR 后 |
| `security-review` | 安全审查当前分支改动 | **必用（提审前）** | 小程序提审前、生产上线前 |

### B. 与本项目无关（已有但不用）

| Skill | 原用途 | 不适用原因 |
|-------|--------|-----------|
| `keybindings-help` | 自定义键盘快捷键 | PinDou 不涉及 |
| `coach` / `insight` / `log-trade` / `weekly-review` / `x-digest` | 用户的交易系统（Hermes / 心法项目） | 项目隔离 |

### C. 用户期望但本地缺失（需 Codex 上 GitHub 搜补）

> 用户明确要求：Skills 不仅看本地，还要让 Codex 去 GitHub 搜好用的来决定最终使用。下列是用户在 handoff 文档 5.1 节列出的、当前本地未加载的 skill 方向，Codex 在 Phase 0 期间负责扫描候选：

| 期望方向 | 用途 | 候选关键词（给 Codex） |
|---------|------|------------------------|
| `frontend-design` | UI / 视觉设计辅助 | `awesome-claude-skills`, `claude-frontend-design`, `figma-skill` |
| 产品文档类（PRD / PRFAQ / Spec） | Phase 1 写 PRD 用 | `claude-prd-skill`, `prfaq-template`, `product-spec-generator` |
| 调研类（research / analysis） | 提升 Codex 调研效率 | `research-skill`, `competitor-analysis-skill` |
| 社区 awesome-design 类 | 设计资源 / 灵感聚合 | `awesome-design`, `awesome-pixel-art` |
| 大厂级流程类（SOP / checklist / ADR） | 流程模板 | `awesome-adr`, `engineering-sop-templates` |

**Codex 调研要求**（合并入 Phase 0 任务清单，详见 `codex_briefs/`）：
- 在 GitHub 搜索上述关键词
- 每个候选 skill 写一段：仓库 / star 数 / 最近更新 / 协议 / 集成成本 / 推荐指数
- 输出到 `01_research/tech/skills_candidates.md`
- 推荐 Top 3 由用户审核后再决定是否本地安装

## 二、决策原则
- **必用** skill：在对应 Phase 启动前必须验证可用、跑通最小用例
- **备选** skill：按需启用，不强求
- **GitHub 补充**：以"协议宽松（MIT/Apache 2.0）+ 最近半年有更新 + star > 50"为筛选门槛
- 任何引入的 skill 必须在本文件追加记录（名称、用途、来源、引入日期）

## 三、更新记录
| 日期 | 变更 | 操作人 |
|------|------|--------|
| 2026-05-24 | 初版盘点 | Claude Code |
