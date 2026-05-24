# 决策日志

> 所有重大决策按 ADR 格式记录到 `04_architecture/ADRs/`，本文件作为索引。
> 决策流程：用户 + chat 端 Claude 拍板 → Claude Code 落档 → 后续 Codex / Gemini 执行。

## ADR 索引

| 编号 | 标题 | 状态 | 日期 | 链接 |
|------|------|------|------|------|
| ADR-001 | 平台策略：小程序优先 + Web 预埋 | Accepted | 2026-05-24 | [文件](../04_architecture/ADRs/ADR-001-platform-strategy.md) |
| ADR-002 | 色卡支持：MARD + COCO 双色卡 | Accepted | 2026-05-24 | [文件](../04_architecture/ADRs/ADR-002-color-palette.md) |
| ADR-003 | 变现结构：免费 + 广告 + AI付费 + 人工精修 | Accepted | 2026-05-24 | [文件](../04_architecture/ADRs/ADR-003-monetization.md) |
| ADR-004 | 冷启动渠道：小红书账号矩阵 | Accepted | 2026-05-24 | [文件](../04_architecture/ADRs/ADR-004-cold-start.md) |
| ADR-005 | AI 风格化技术方案：多路线 + fallback | Accepted | 2026-05-24 | [文件](../04_architecture/ADRs/ADR-005-ai-stylization.md) |
| ADR-005a | 写实人像 GPU 决策延后到 PoC 数据驱动 | Accepted | 2026-05-24 | [文件](../04_architecture/ADRs/ADR-005a-poc-driven-gpu-decision.md) |
| ADR-006 | 小程序主体：个人 | Accepted | 2026-05-24 | [文件](../04_architecture/ADRs/ADR-006-mp-subject-individual.md) |
| ADR-007 | 不预订国产合规 Provider 应急切换 | Accepted | 2026-05-24 | [文件](../04_architecture/ADRs/ADR-007-no-compliance-provider.md) |
| ADR-008 | Phase 1 双交付物：FinishedPreview + PatternSheet 拆分 | Accepted | 2026-05-24 | [文件](../04_architecture/ADRs/ADR-008-preview-pattern-split.md) |
| ADR-009 | 私人素材处置规则：不入 Git + 摘要规则 | Accepted | 2026-05-24 | [文件](../04_architecture/ADRs/ADR-009-private-asset-handling.md) |

## ADR 模板

新 ADR 复制以下模板到 `04_architecture/ADRs/ADR-NNN-short-title.md`：

```markdown
# ADR-NNN: 标题

- **状态**: Proposed / Accepted / Deprecated / Superseded by ADR-XXX
- **日期**: YYYY-MM-DD
- **决策者**: 用户 + chat 端 Claude
- **影响范围**: Phase / 模块 / 端

## 背景
描述触发该决策的问题或需求。

## 决策
明确的"我们决定 X"。

## 理由
为什么是 X 而非 Y/Z。

## 后果
- 正面：…
- 负面：…
- 风险：…

## 备选方案
列出考虑过但未采纳的方案，及未采纳的原因。
```

## 评审记录索引
chat 端 Claude 的阶段性评审意见归档到对应阶段目录，本表索引。

| 评审日期 | 评审对象 | 结论 | 归档位置 |
|----------|----------|------|----------|
| —        | —        | —    | —        |
