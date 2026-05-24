# ADR-008: Phase 1 双交付物 — FinishedPreview + PatternSheet 拆分

- **状态**: Accepted
- **日期**: 2026-05-24
- **决策者**: 用户 + Claude Code（基于 Codex Task C 私有素材实验 + 拼豆领域调研）
- **影响范围**: Phase 1 PRD、`StylizationProvider` 接口设计、Phase 2 后端架构、ADR-003 定价分层

## 背景
Codex Task C 私有素材实验和 `perler_bead_domain_notes.md` 拼豆领域调研一致显示：
- 用户购买决策几乎完全由"成品好不好看"驱动（FinishedPreview 价值）
- 但**真正能让用户拼出来**需要严肃的图纸（PatternSheet 价值）
- 两者**生成方式、失败模式、计算成本、用户预期完全不同**

把这两个交付物绑在同一个接口 / 同一次生成里，会让架构永远在"既要又要"之间妥协。

## 决策

### 拆为两个独立交付物 + 两个独立接口

```
┌──────────────────────┐         ┌──────────────────────┐
│  FinishedPreview     │         │  PatternSheet        │
│  （成品预览，AI 生成） │  ──→    │  （制作图纸，程序化） │
├──────────────────────┤         ├──────────────────────┤
│ 用户购买决策依据      │         │ 付费解锁 / 实际制作   │
│ 圆豆渲染 / 风格化     │         │ 网格 + 色号 + 数量   │
│ 12-24 色             │         │ 同 palette          │
│ 主体 + 透明背景       │         │ 同 size             │
└──────────────────────┘         └──────────────────────┘
        ↑                                  ↑
   PreviewProvider                  PatternBuilder
   (外部 API，不稳定)               (本地算法，确定)
   接口规范见下                      接口规范见下
```

### `PreviewProvider` 接口（外部 AI）
```
PreviewProvider.generate(image, style_preset, size_preset) → FinishedPreview
  输入：原图 + 风格预设（Q版人像 / Q版宠物 / Q版情侣 / 通用卡通）+ 尺寸预设
  输出：FinishedPreview（PNG，带 alpha，背景透明，目标色数 12-24）+ metadata(cost, latency)
  失败：触发 fallback chain（主反代 → 备 → 普通量化兜底）
  实现：当前 P1 反代 gpt-image-2；接口签名为 Phase 2 切换 / 多 provider 留出空间
```

### `PatternBuilder` 接口（本地确定性算法）
```
PatternBuilder.build(preview, size, brand, bead_diameter) → PatternSheet
  输入：FinishedPreview + 目标网格尺寸（60×80 / 80×100 / 100×120）+ 品牌 + 豆径
  输出：PatternSheet 结构体：
    - grid[][]: 二维网格，每格指向 color_id 或 NoBead
    - color_counts: { color_id: 颗数 }
    - bead_total: 总颗数
    - coords: 可导出 Excel/PDF 的坐标表
    - no_bead_mask: 哪些格不放豆（透明背景区）
    - palette_used: 实际用到的色号子集
  失败：bug fix（不应失败，是确定性算法）
  实现：Phase 2 后端，依赖 Task B 推荐组合 (K-means + CIEDE2000 + 无抖动) + 拼豆后处理
```

### 用户路径（Phase 1 PRD 起点）
1. 上传图 → 选风格 + 尺寸 → 触发 `PreviewProvider`
2. 看 FinishedPreview → 可重生成 / 调风格（重复 1）→ 满意了"加入待制作"
3. 付费解锁 / 看广告 → 触发 `PatternBuilder` → 看 PatternSheet
4. 下载图纸（基础：简单网格；高级：PDF + Excel + 分区图 + 购物清单）

### 定价分层对齐（修订 ADR-003 触发）
- 基础包（9.9 单次）：FinishedPreview + 简单网格 PatternSheet
- 高级包（28 月卡）：FinishedPreview 不限 + 高级 PatternSheet（PDF + Excel + 分区图 + 多规格切换）
- 人工精修（99 起）：人工兜底高难度场景，跨 Preview + Pattern 都包

## 理由
- 单一职责让架构演化容易
- 用户路径"先看预览 → 付费解锁图纸"和定价分层天然对齐
- Preview 失败和 Pattern 失败处理逻辑完全不同，不应共享接口
- Phase 2 后端开发可以分两条线并行（Preview 集成、Pattern 算法），减少阻塞

## 后果

### 正面
- 接口清晰，Phase 1 PRD 起点明确
- Phase 2 后端可以两人并行开发
- 用户付费路径清晰可营销

### 负面
- Phase 1 需要设计两套契约 + Phase 2 需要实现两套
- 用户体验需要确保"Preview → Pattern"切换流畅，不会断点

### 风险
- Preview 生成耗时（当前 P1 P95 ~60s）会影响用户体验，需要 Phase 1 PRD 设计"等待 UX"

## 备选方案
- **单接口一次返回 Preview + Pattern**：被否，失败语义混乱、定价分层失去意义
- **Preview 即 Pattern**（不做拆分）：被否，Preview 是 AI 不确定输出，直接拿去做严肃图纸会出错

## 关联
- 修订 ADR-005 / ADR-005a（路线收敛到 Q 版 + 接口拆分）
- 修订 ADR-003 定价分层（已对齐）
- 关联 Task B 量化推荐（K-means + CIEDE2000 + 无抖动）作为 PatternBuilder 算法基础
- 关联 ADR-002 / Task H（PatternBuilder 需要全品牌全规格 palette）
- 关联 perler_bead_domain_notes.md（拼豆后处理规则纳入 PatternBuilder）
