# Task G — GitHub Skills 候选搜索

**Status**: completed (Codex @ 2026-05-24) — 产出：[skills_candidates.md](../../01_research/tech/skills_candidates.md)
**Owner**: Codex
**Priority**: 低
**Estimated**: 0.5-1 天
**依赖**: 无

---

## 背景
用户明确要求：当前 Claude Code 环境本地 skill 不全，希望 Codex 上 GitHub 找好用的候选，由用户审核后决定是否本地安装。

详细需求方向见 `00_meta/skills_inventory.md` 第一节 C 部分。

## 目标
扫描 GitHub 上 Claude Code skill 相关仓库，挑出 Top 候选，写一份对比报告。

---

## 搜索关键词

### 必搜
- `claude-code-skills`
- `claude-skills`
- `awesome-claude-code`
- `awesome-claude-skills`

### 期望方向（按 `skills_inventory.md` C 部分）
| 方向 | 候选关键词 |
|------|-----------|
| frontend-design | `claude-frontend-design`, `figma-claude`, `claude-ui-skill` |
| 产品文档（PRD / PRFAQ / Spec） | `claude-prd-skill`, `prfaq-template`, `product-spec-skill`, `claude-product-skill` |
| 调研类 | `claude-research-skill`, `competitor-analysis-skill`, `claude-deepresearch` |
| 设计资源聚合 | `awesome-design`, `awesome-pixel-art`, `awesome-ui-design` |
| 工程流程模板 | `awesome-adr`, `engineering-sop-templates`, `claude-engineering-skill` |

## 筛选门槛
- 协议宽松（MIT / Apache 2.0 / BSD）—— 必须
- 最近半年有更新 —— 优先
- Star > 50 —— 优先
- 有 README + 示例 —— 必须

## 每个候选产出格式
```markdown
### [仓库名]
- **链接**：
- **Star / Forks**：
- **最近 commit**：
- **协议**：
- **维护状态**：
- **核心能力**：（一句话）
- **对 PinDou 项目的价值**：（具体用在哪个阶段 / 哪个任务）
- **集成成本**：（低 / 中 / 高，需要哪些前置）
- **推荐指数**：（必装 / 推荐 / 可选 / 不推荐）
- **风险**：（如：作者活跃度低 / 依赖闭源 LLM 等）
```

## 输出位置
- 主报告：`01_research/tech/skills_candidates.md`

## 报告末尾必须有
- **Top 3 推荐**（用户最该装的，附理由）
- **避雷清单**（看起来好用但实际有问题的）
- **本地集成步骤**（用户拍板后怎么装到 `~/.claude/skills/`）

## 验收标准
- [ ] 至少扫描 5 个方向
- [ ] 候选总数 ≥ 15 个
- [ ] Top 3 推荐有具体落地用法
- [ ] `data_sources.md` 追加引用

## 不要做
- ❌ 不要直接 fork / 安装到用户环境（用户最终决定）
- ❌ 不要推荐协议有问题的（GPL / 商用受限）
