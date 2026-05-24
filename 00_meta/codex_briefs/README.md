# Codex 任务 Brief 索引

> 给 Codex（后端 + 调研执行 AI）的 Phase 0 任务清单。
> Codex 在新会话启动后第一步：**通读本 README + PROJECT_CHARTER + 全部 ADR（已 9 个）+ FUTURE_WORK**，然后认领任务。
> 任务可并行，但 D 色卡的输出会被 B 算法横评和 C PoC 引用，**建议 D 优先启动**。
>
> **2026-05-24 更新**：A-G 已 completed；新增 Task H（全品牌全规格豆系信息库），是 Phase 1 启动前最后一个调研任务。

---

## 前置阅读（必读，不读不许开工）

按顺序读：
1. `../../README.md` — 项目总览
2. `../PROJECT_CHARTER.md` — 一页纸目标、范围、里程碑、风险、角色
3. `../../04_architecture/ADRs/ADR-001-platform-strategy.md` — 平台策略
4. `../../04_architecture/ADRs/ADR-002-color-palette.md` — 双色卡
5. `../../04_architecture/ADRs/ADR-003-monetization.md` — 变现结构
6. `../../04_architecture/ADRs/ADR-004-cold-start.md` — 冷启动渠道
7. `../../04_architecture/ADRs/ADR-005-ai-stylization.md` — AI 风格化技术方案
8. `../../04_architecture/ADRs/ADR-005a-poc-driven-gpu-decision.md` — **重要**：写实人像 GPU 决策延后，PoC 必须用量化输出图主观投票
9. `../../04_architecture/ADRs/ADR-006-mp-subject-individual.md` — 小程序个人主体（影响类目 / 备案 / 支付路径）
10. `../FUTURE_WORK.md` — 后续待决策事项（影响你产出的边界）
11. `../api_inventory.md` — API 资源清单（key 走 `.env`，不要硬编码）

---

## 任务清单

| 编号 | 文件 | 主题 | 优先级 | 预计工时 |
|------|------|------|--------|----------|
| A | `task_A_existing_tools.md` | 现有拼豆 / 像素化工具拆解 | 中 | 1-2 天 |
| B | `task_B_algorithms.md` | 算法方案横评（量化 / 色差 / 抖动） | 高 | 2-3 天 |
| **C** | `task_C_ai_poc.md` | **AI 预处理纯 API PoC（核心）** | **最高** | **3-5 天** |
| **D** | `task_D_colormap.md` | **色卡数据库（先启动）** | **高** | 1-2 天 |
| E | `task_E_competitor.md` | 竞品商业模型 + 小红书账号 | 中 | 1-2 天 |
| F | `task_F_compliance.md` | 合规调研 | 高 | 2-3 天 |
| G | `task_G_skills_github.md` | GitHub Skills 候选搜索 | 低 | 0.5-1 天 |
| **H** | `task_H_bead_db_full.md` | **全品牌全规格豆系信息库（Phase 1 启动前必须完成）** | **高** | **3-4 天** |

**推荐执行顺序**：D 先启动 → B / C 并行依赖 D → A / E / F / G 自由穿插 → **H 在 Phase 0 收尾启动**（A-G 已完成）。

---

## 通用规则（每个任务都遵守）

### 1. 数据源留痕
任何外部数据（爬取 / API / 论文 / 文档）必须在 `../data_sources.md` 追加一条，按文件中模板填。

### 2. 产出文件位置
每个任务的输出位置在对应 brief 里写明。**禁止把产出放到根目录或乱放**。

### 3. 不写 key
任何代码 / 文档 / commit 不允许出现 API key 本体。统一走环境变量（`.env` 已 gitignore，模板见 `.env.example`）。

### 4. 不引用旧决策
ADR-005 写过"gpt-image-1"，但实际可用模型是 **gpt-image-2**。
**2026-05-24 修订重点**（与 Task C 完成后的产品方向转向一致）：
- ADR-005a 已修订：转 Q 版 FinishedPreview 主路线，关闭 GPU 决策路径，删除 5 人投票要求
- ADR-008 新增：Phase 1 双交付物（FinishedPreview + PatternSheet）+ PreviewProvider / PatternBuilder 接口拆分
- ADR-009 新增：私人素材**严禁** commit（user_poc_private/ 已 gitignore）
- ADR-002 修订：色卡信息库要全（Task H），产品默认 MARD 5mm

### 5. 私人素材处置（ADR-009 hard rule）
- 真人 / 第三方版权 / 用户提供的素材 → **绝对不 commit**
- 实验完成产出**摘要文档**进 git（位置：`01_research/tech/private_run_summaries/<run_id>.md`）
- 不确定就在 `_questions_for_user.md` 问

### 6. Commit 规范
- 分支：`phase0`（已存在）
- 每个任务完成后单独 commit：`docs(phase0-task-X): 简短描述`
- 大改动拆多个 commit，不要一次 push 几百个文件

### 7. 进度同步
- 启动任务前：在 brief 文件顶部加一行 `**Status**: in_progress (Codex @ YYYY-MM-DD)`
- 完成后：`**Status**: completed (Codex @ YYYY-MM-DD)` + 链接到产出文件
- 受阻：`**Status**: blocked - 原因`，并在本 README 末尾 "受阻清单" 追加

### 8. 评审流程
任务完成后**先不要合并到 main**，留在 phase0 分支。由用户带回 chat 端 Claude 评审，评审通过 Claude Code 才合并。

---

## 受阻清单（实时维护）
（任务受阻时追加，注明原因 + 需要谁帮）

- 2026-05-24 — Task C P1 key blocker resolved：用户已在本地 `.env` 补齐 P1 key；P1 `gpt-image-2` 已跑通 40/40 API 样本并产出量化图。Task C Codex 交付已完成，5 人主观投票由用户线下组织。

---

## Phase 0 出口验收（由 Claude Code 检查）
- [x] 7 个任务全部 `completed`
- [ ] 任务 C 必须有**量化输出图**实际样本，不是只有 AI 生成的原图
- [ ] `data_sources.md` 每条外部引用都有记录
- [ ] 所有 commit message 符合规范
- [ ] 综合简报 `phase0_summary.md` 由 Claude Code 撰写完成
