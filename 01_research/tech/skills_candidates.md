# GitHub Skills 候选搜索报告

> 抓取日期：2026-05-24  
> 筛选口径：优先 MIT / Apache-2.0 / MIT-0 / CC0 / BSD 等宽松协议；Star / Fork / 最近更新来自 GitHub API 截面，后续会变化。部分 Claude skill 仓库 star 异常偏高，推荐时更看 license、README、目录结构和是否有 `SKILL.md`。

## 候选清单

| 仓库 | 方向 | Star / Fork | 最近更新 | 协议 | 核心能力 / PinDou 价值 | 成本 | 推荐 |
|------|------|-------------|----------|------|--------------------------|------|------|
| [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | 综合 skills / PRD / 竞品 / 合规 | 16071 / 2210 | 2026-05-24 | MIT | 329 个 Claude/Codex skills，含 `code-to-prd`、`competitive-intel`、`competitive-teardown`、`autoresearch-agent`、合规类；适合补齐 Phase 0/1 调研与产品文档工作流 | 中 | 必装候选 |
| [phuryn/pm-skills](https://github.com/phuryn/pm-skills) | PRD / PM / Spec | 11607 / 1375 | 2026-05-20 | MIT | PM skills marketplace，含 `create-prd`、roadmap、job stories、pre-mortem；适合 Phase 1 写 PRD、需求拆解、验收口径 | 低 | 必装候选 |
| [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) | frontend-design | 82248 / 8475 | 2026-04-03 | MIT | 直接包含 `.claude/skills/*/SKILL.md`，覆盖 banner、brand、design-system；适合小程序 UI、品牌调性、视觉规范 | 低-中 | 必装候选 |
| [mattpocock/skills](https://github.com/mattpocock/skills) | 工程 SOP / 架构审查 | 103348 / 9136 | 2026-05-20 | MIT | 工程类 skills，含 ADR、架构改进、prototype、diagnose；适合 Phase 2+ 代码质量和工程评审 | 低 | 推荐 |
| [OneWave-AI/claude-skills](https://github.com/OneWave-AI/claude-skills) | 综合 skills | 155 / 24 | 2026-04-10 | MIT | 162 个 `SKILL.md`，含 accessibility、brand、API docs、agent team；适合补充通用工作流 | 低 | 推荐 |
| [w95/awesome-claude-corporate-skills](https://github.com/w95/awesome-claude-corporate-skills) | 竞品 / 深研 / 商业分析 | 41 / 13 | 2026-02-26 | MIT | 166 个企业角色 skills，含 competitive-analysis、deep-research、strategic-planning；Star 未过 50，但目录对商业调研贴合 | 低 | 可选 |
| [fvadicamo/dev-agent-skills](https://github.com/fvadicamo/dev-agent-skills) | GitHub / skill authoring | 63 / 5 | 2026-05-17 | MIT | Git commit、PR creation/review/merge、creating-skills；适合后续规范化本地 skill 制作和 PR 流程 | 低 | 推荐 |
| [github/spec-kit](https://github.com/github/spec-kit) | Spec-driven development | 105493 / 9316 | 2026-05-22 | MIT | GitHub 官方 spec-driven toolkit；适合把 PinDou Phase 1 PRD 转成 specs/tasks/implementation plan | 中 | 推荐 |
| [snarktank/ai-dev-tasks](https://github.com/snarktank/ai-dev-tasks) | PRD -> task | 7727 / 1741 | 2025-11-05 | Apache-2.0 | 简单 AI dev task 管理，根目录有 `create-prd.md`；适合轻量 PRD 到任务拆解 | 低 | 推荐 |
| [punt-labs/prfaq](https://github.com/punt-labs/prfaq) | PRFAQ | 22 / 3 | 2026-05-11 | MIT | Amazon Working Backwards PR/FAQ，含 `skills/prfaq/SKILL.md`；适合 Phase 1 做 PRFAQ 补充 | 低 | 可选 |
| [aws-samples/sample-kiro-cli-prompts-for-product-teams](https://github.com/aws-samples/sample-kiro-cli-prompts-for-product-teams) | PRD / PRFAQ / market research | 30 / 5 | 2026-05-04 | MIT-0 | AWS samples，含 PRD、PRFAQ、market research、design system prompts；适合改造成 product skill | 中 | 可选 |
| [assafelovic/gpt-researcher](https://github.com/assafelovic/gpt-researcher) | deep research | 27264 / 3666 | 2026-04-16 | Apache-2.0 | 深度研究 agent，含 `.claude/SKILL.md`；可借鉴 Task E/F 调研流程，但运行依赖较重 | 高 | 推荐 |
| [langchain-ai/open_deep_research](https://github.com/langchain-ai/open_deep_research) | deep research | 11488 / 1639 | 2026-05-19 | MIT | LangChain 深度研究参考实现；适合研究 pipeline 参考，不建议直接塞进 Claude skills | 高 | 可选 |
| [Shubhamsaboo/awesome-llm-apps](https://github.com/Shubhamsaboo/awesome-llm-apps) | research / competitor | 111663 / 16585 | 2026-05-23 | Apache-2.0 | 含 competitor intelligence agent team 示例；适合 Task E 竞品流程参考 | 中 | 可选 |
| [zubair-trabzada/ai-marketing-claude](https://github.com/zubair-trabzada/ai-marketing-claude) | 竞品 / 营销 | 1752 / 562 | 2026-03-02 | MIT | Claude marketing suite，含 `market-competitors/SKILL.md`、竞品扫描脚本；适合小红书/竞品落地页分析 | 中 | 推荐 |
| [bradtraversy/design-resources-for-developers](https://github.com/bradtraversy/design-resources-for-developers) | design resources | 65743 / 12051 | 2026-05-24 | MIT | 设计/UI 资源聚合；适合补充 UI inspiration、图标、配色、素材来源 | 低 | 推荐 |
| [Siilwyn/awesome-pixel-art](https://github.com/Siilwyn/awesome-pixel-art) | pixel art resources | 1207 / 48 | 2026-05-18 | CC0-1.0 | 像素艺术资源聚合；适合 PinDou 像素化 / 拼豆风格参考 | 低 | 推荐 |
| [adr/madr](https://github.com/adr/madr) | ADR / engineering SOP | 2218 / 458 | 2026-04-17 | MIT OR CC0-1.0 | Markdown ADR 模板；适合延续 `04_architecture/ADRs/` 的决策记录规范 | 低 | 推荐 |
| [nexu-io/open-design](https://github.com/nexu-io/open-design) | design system / prototype | 51154 / 5836 | 2026-05-24 | Apache-2.0 | Local-first Claude Design 替代，含设计系统、prototype、导出能力；能力强但体量大 | 高 | 可选 |

## Top 3 推荐

1. [phuryn/pm-skills](https://github.com/phuryn/pm-skills)  
   最贴 Phase 1：`create-prd`、roadmap、pre-mortem、job stories 可以直接服务 PRD / spec 产出。

2. [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill)  
   最贴 frontend / design：直接有 `.claude/skills`，可先挑 `brand`、`design-system`，用在小程序视觉规范和页面设计审查。

3. [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills)  
   覆盖面最广：`competitive-intel`、`code-to-prd`、`autoresearch-agent`、合规 / 商业类 skill 对 Phase 0 后续缺口有补位价值。

## 避雷清单

- [anthropics/skills](https://github.com/anthropics/skills)：官方 Agent Skills 仓库，但 GitHub API 未识别 license，根目录未见标准 license；可参考，不建议复制安装进项目。
- [BehiSecc/awesome-claude-skills](https://github.com/BehiSecc/awesome-claude-skills)：Star 高、目录全，但 license 未识别；不满足本任务筛选门槛。
- [hesreallyhim/awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code)：license 为 CC BY-NC-ND 4.0，含非商业 / 禁止演绎限制，不适合纳入可复用候选。
- [architecture-decision-record/architecture-decision-record](https://github.com/architecture-decision-record/architecture-decision-record)：ADR 示例多，但 README 自述内容为 CC BY-NC-SA，不满足宽松协议。
- [ComposioHQ/awesome-claude-skills](https://github.com/ComposioHQ/awesome-claude-skills)：搜索命中且 Star 高，但 license 缺失；先不推荐。
- [eyaltoledano/claude-task-master](https://github.com/eyaltoledano/claude-task-master)：功能看似贴任务管理，但 license 为 Other / 未明确；先不推荐。
- [goabstract/Awesome-Design-Tools](https://github.com/goabstract/Awesome-Design-Tools)：MIT，但最近 push 停在 2024-07；可偶尔查灵感，不列 Top。

## 本地集成步骤

1. 用户先拍板 Top 候选，不要整仓库无脑复制。
2. 每个仓库只挑需要的 skill 目录，例如 `create-prd/SKILL.md`、`design-system/SKILL.md`、`competitive-intel/SKILL.md`。
3. 复制到 `~/.claude/skills/<skill-name>/`，保留 `SKILL.md`、references、scripts。
4. 打开 `SKILL.md` 检查触发描述是否和 PinDou 冲突；必要时改成本项目口径。
5. 在 `00_meta/skills_inventory.md` 追加：名称、用途、来源、引入日期。
6. 跑最小用例：让 Claude / Codex 生成一段 PRD、竞品分析或 UI review，确认 skill 会被触发。
7. 若 skill 需要 API、爬虫或第三方服务，只写环境变量名，不写 key 本体。
