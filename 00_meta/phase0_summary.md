# PinDou — Phase 0 综合简报

> **日期**：2026-05-24
> **撰写人**：Claude Code
> **分支**：`phase0`（未合并到 main，待评审）
> **目的**：Phase 0 出口评审 + Phase 1 PRD 起点输入

---

## 0. TL;DR

Phase 0 启动到收尾共一天，完成 7 个 Codex 调研任务 + 9 个 ADR 决策 + 一次重要的产品方向转向。产品形态从最初的"AI 写实人像 + 量化拼豆图纸"演化为"Q 版 FinishedPreview + 程序化 PatternSheet 双交付"。技术路线从"反代主 + 国产备 + GPU 兜底"收敛为"纯反代 API + 普通量化兜底"。用户接受了反代合规风险作为成本换效率的取舍（ADR-007 留痕）。新增 Task H（全品牌豆系信息库）作为 Phase 1 启动前最后一个调研任务。

**给 Phase 1 PRD 的核心起点**：
1. 双交付物 = `FinishedPreview` + `PatternSheet`（ADR-008）
2. 两个接口 = `PreviewProvider`（外部 AI）+ `PatternBuilder`（本地确定性算法）
3. 量化算法基线 = K-means + CIEDE2000 + 无抖动（Task B 反直觉结论）
4. 色卡基线 = MARD 5mm 默认开启 / 信息库支持全品牌全规格（Task H 待跑）
5. 用户路径 = 上传 → 选风格尺寸 → 看 Preview → 加购 → 付费解锁 Pattern

---

## 1. Phase 0 时间线

| 节点 | 内容 | 关键产出 |
|------|------|----------|
| T+0 | 项目 bootstrap | 目录、Git、Charter、ROADMAP、5 ADR、Skills/API 盘点 |
| T+1 | 与用户对话 #1：纯 API 转向 | ADR-005a（GPU 决策延后到 PoC）+ FUTURE_WORK |
| T+2 | 与用户对话 #2：个人主体 | ADR-006、7 个 Codex briefs（A-G） |
| T+3 | Codex 全部交付 + 安全提交 redact 泄露 key | 12 个 commit，phase0 分支 |
| T+4 | 用户私有素材实验 → 产品方向转向 | 拼豆领域知识、Q 版方向、prompt 约束、双交付物概念 |
| T+5 | 与用户对话 #3：反代合规、服务器、主体路径 | ADR-007（用户接受反代风险） |
| T+6 | 与用户对话 #4：色卡信息库要全、转 Q 版 | ADR-002 修订 + ADR-005a 修订 + ADR-008/009 新增 + Task H 派单 |
| T+7（当前） | 综合简报 + Phase 0 收尾 | 本文件、Task H 进行中 |

---

## 2. 决策演化（9 个 ADR）

| ADR | 状态 | 决策 | 修订史 |
|-----|------|------|--------|
| **ADR-001** | Accepted | 平台：小程序优先 + Web 预埋 | — |
| **ADR-002** | Accepted（修订版） | 色卡：信息库尽量全 + 产品默认 MARD 5mm | 取代首版"双色卡收敛"思路 |
| **ADR-003** | Accepted | 变现：免费 3 次 + 广告续次 + AI 付费 + 人工精修 | 待 Phase 1 PRD 时按 ADR-006 个人主体限制 + ADR-008 双交付物再细化 |
| **ADR-004** | Accepted | 冷启动：小红书账号矩阵（用户女朋友主导） | — |
| **ADR-005** | Accepted | AI 风格化：多路线 + StylizationProvider 抽象 + fallback chain | 主表中"GPU 自部署"行已被 ADR-005a 关闭 |
| **ADR-005a** | Accepted（修订版） | 转 Q 版 FinishedPreview 主路线 / 关闭 GPU 决策 / 删 5 人投票 | 取代首版"PoC 投票决定 GPU" |
| **ADR-006** | Accepted | 小程序主体：个人 | 触发升级条件见 FUTURE_WORK 第 6 条 |
| **ADR-007** | Accepted | 不预订国产合规 Provider 应急切换 | 用户原话留痕，接受风险 |
| **ADR-008** | Accepted | Phase 1 双交付物：FinishedPreview + PatternSheet 拆分 | 来自 Task C 实验 + 拼豆领域调研 |
| **ADR-009** | Accepted | 私人素材处置：不入 Git + 摘要规则 | 跨境合规 + 商标 + 第三方版权 |

**决策演化的最大转折点**：T+4 用户私有素材实验。在那之前 Phase 0 在解"AI 风格化怎么做最好"；在那之后 Phase 0 在解"拼豆产品的最优交付形态是什么"——后者是更高维度的问题，决定了 Phase 1 PRD 的起点和 Phase 2 后端架构的形态。

---

## 3. 七个 Codex 任务的产出 + 关键发现

### Task A — 现有工具拆解
- 产出：`01_research/tech/existing_tools.md` + `github_landscape.md` + `competitor_samples/`
- 关键发现：业界对真实人像普遍失真；多数工具用脚本量化 + RGB 最近邻；GitHub SOTA（如 IPAdapter / PhotoMaker）是开源 SD 生态资产，封闭 API 不暴露同等控制器
- 对 PinDou 影响：差异化卖点（人像 / 宠物 / 情侣 + AI 预处理）在赛道内有空白

### Task B — 算法横评
- 产出：`01_research/tech/algorithms.md` + `algorithm_metrics.csv`（36 行）+ `algorithm_impls/` + `algorithm_samples/`
- 测试矩阵：3 张测试图 × 12 个量化 × 色差 × 抖动组合
- **反直觉发现（重要）**：Floyd-Steinberg 抖动在 100×100 拼豆场景下**反而降质**（噪点 + SSIM 下降）。**K-means + CIEDE2000 + 无抖动**（C02 / C12）是写实 / 宠物 / 卡通三类的统一最优
- 对 PinDou 影响：PatternBuilder 算法基线已确定，Phase 2 后端不需要在抖动算法上花时间

### Task C — AI 预处理 PoC（核心）
- 产出：`01_research/tech/poc_runner.py` + `prompts.md` + `perler_bead_domain_notes.md` + 40 条 API 结果 + 120 张样本 + `subjective_vote_template.csv`
- 私有素材实验（不入 git）：`graduation_couple_q_chibi/` + `pet_batch_20260524/`
- 关键发现 1：合成测试图能证明流程，不能证明商业质量；必须用真实素材测产品方向
- 关键发现 2：**应该转向"Q 版成品预览图 → 程序化图纸"双交付**，AI 不该负责严肃图纸
- 关键发现 3：**Prompt 必须约束"不新增原图没有的身体部位"**（情侣半身照被模型补了腿和脚）
- 关键发现 4：拼豆"颜色少 / 块面干净 / 粗黑边 / 透明背景"是产品级要求，不是 AI 默认输出
- 对 PinDou 影响：直接催生 ADR-005a 修订 + ADR-008 拆分双交付物
- API 调用指标：P50 33s / P95 60s / 成功率 40/40（合成图集）

### Task D — 色卡数据库
- 产出：MARD 5mm 291 色 + COCO 5mm 80 色 + 跨色卡对照 1746 行 + 可视化 palette 图 + README
- 数据源：交叉验证 ≥ 2 个来源；价格按"采集时挂牌价"留痕
- 对 PinDou 影响：作为 Task H 全品牌扩展的起点 + Phase 2 PatternBuilder 的 palette 数据基础

### Task E — 竞品 + 小红书
- 产出：`competitor/business_models.md` + `xhs_accounts.md` + `08_growth/xhs_playbook.md`
- 关键发现：拼豆赛道 Top 小程序对人像基本不做 AI 预处理；小红书"云朵豆原创图纸"类账号的成功模式可借鉴
- 对 PinDou 影响：差异化卖点 + 引流话术 + 标题套路有 5+ 内容点

### Task F — 合规调研
- 产出：`01_research/compliance/compliance_checklist.md`
- **三个硬结论**：
  1. **个人主体不建议直接做 AIGC 商业化**（但法律未明禁，问题在微信小程序平台规则 + AIGC 类目审核难度）
  2. **日本服务器存中国用户人像 = 跨境敏感个人信息**，应按 PIA + 标准合同备案处理
  3. **MARD / COCO 品牌名**可作"兼容描述"使用，不得暗示官方授权
- 对 PinDou 影响：直接催生 ADR-006 触发条件 + ADR-007 用户接受风险 + FUTURE_WORK 跨境合规升级
- 给用户的产品建议（已部分采纳）：选"工具 > 图像处理"类目，**不**申请 AIGC 类目；隐私政策必须覆盖单独同意 + 删除权 + 短期保存

### Task G — GitHub Skills 候选
- 产出：`01_research/tech/skills_candidates.md`
- 对 PinDou 影响：低优先；用户后续根据需要自行安装

---

## 4. 风险清单（FUTURE_WORK 全量映射）

| # | 风险 | 当前决策 | 触发条件 | 等级 |
|---|------|---------|---------|------|
| 1 | 写实人像功能缺失 | Phase 2+ 可选功能（ADR-005a 修订后） | Phase 2+ 用户反复要求 / 竞品上线 | 低 |
| 2 | 跨境合规（日本服务器存中国用户人像） | MVP 日本机研发；用户已搞到上海 8C16G 20M | Phase 3 提审前 / 用户量 ≥ 1000 / 合规投诉 | 高 |
| 3 | 对象存储迁移 | MVP 本地磁盘 + Nginx | 日 PV > 1000 + 体积 > 50 GB | 中 |
| 4 | AIGC 算法备案 | 不备案 + 走"工具"类目规避 | 提审前 / 用户量 ≥ 1 万 | 高 |
| 5 | Web 端 UI 补齐 | Phase 1 只做骨架 | 小程序月活 > 1 万 + 付费率 > 3% | 低 |
| 6 | 小程序主体升级 | 个人主体 | 类目审核被拒 / 月入 ≥ 1500 触发评估 | 中高 |
| 7 | 多品牌 / 多豆径 UI 暴露 | Phase 1 默认 MARD 5mm；UI 暴露 Phase 2/3 | 用户跨品牌需求 / 后端验证稳定 | 低 |
| 8 | **合规切换触发监控（ADR-007）** | 用户接受反代风险，不预订国产 | 月活 ≥ 1 万 / 任一违规投诉 / 微信审核被拒 / 反代故障 > 6 小时 / 法规变化 | **高（已接受）** |

**最高优先级风险（Claude Code 监控职责）**：第 2 条跨境合规 + 第 4 条 AIGC 备案 + 第 8 条 ADR-007 触发条件。任一条命中，下一次对话开始立刻顶上来提醒。

---

## 5. Phase 1 PRD 起点建议

### 5.1 产品形态（来自 ADR-008）

```
┌─ 用户路径（小程序内） ────────────────────────────────────────────┐
│  上传图 → 选风格预设 + 尺寸预设 → 等待 P50 33s / P95 60s       │
│  → 看 FinishedPreview → 可重生成 / 调参数（重复） → "加入待制作" │
│  → 付费解锁 / 看广告 → 触发 PatternBuilder → 看 PatternSheet    │
│  → 下载图纸（基础：网格图；高级：PDF + Excel + 分区 + 购物清单） │
└────────────────────────────────────────────────────────────────┘
```

### 5.2 两个接口

**`PreviewProvider`**（外部 AI / 不稳定 / 需 fallback）
```
generate(image, style_preset, size_preset) → FinishedPreview
  styles: 写实人像 / Q 版人像 / Q 版宠物 / Q 版情侣 / 通用卡通
  sizes: 60×80 / 80×100 / 100×120
  output: PNG with alpha (transparent bg), 12-24 colors
  current impl: P1 反代 gpt-image-2
  fallback: 主 → 备 → 普通量化兜底（保证不报错）
```

**`PatternBuilder`**（本地算法 / 确定性）
```
build(preview, size, brand, bead_diameter) → PatternSheet
  algorithm: K-means + CIEDE2000 + 无抖动（Task B 推荐）
  brand × diameter: MARD/COCO/Hama/Perler/Artkal × 2.6/5/10mm（Task H 输出）
  output: grid[][], color_counts, bead_total, coords, no_bead_mask, palette_used
  postprocess: 去孤点、轮廓保护、局部多数滤波、色数预算
```

### 5.3 风格预设（Phase 1 收敛）
- Q 版人像（默认）
- Q 版宠物
- Q 版情侣
- 通用卡通
- 写实人像 → Phase 2+ 可选

### 5.4 尺寸预设（Phase 1 三档）
- 60×80（小尺寸，~30 元材料成本，宠物 / 单人头像）
- 80×100（中尺寸，~80 元材料成本，单人半身 / 双宠物）
- 100×120（大尺寸，~150 元材料成本，情侣 / 全身像）

### 5.5 定价分层（修订 ADR-003 入口）
- 基础包（9.9 单次）：1 次 Preview 生成 + 基础网格 PatternSheet
- 月卡（28 元）：不限 Preview 重生成 + 5 次 PatternSheet + PDF/Excel 高级图纸
- 人工精修（99 起）：人工兜底 + 任意尺寸 + 自定义色卡

**注意**：ADR-006 限制下，小程序内不能官方微信支付，需要"加客服扫码"或外部 H5 支付替代。Phase 1 PRD 用户路径中"付费解锁"步骤的具体实现需要单独决策。

### 5.6 用户体验细节（必须 PRD 覆盖）
- Preview 生成等待 30-60s 的 UX（进度条 / 趣味文案 / 提示用户去看示例作品）
- 风格 / 尺寸调整 → Preview 重生成 → API 调用计费如何与免费 3 次额度匹配
- 私人素材处理（ADR-009 hard rule）：用户上传图本地处理后**短期保存 + 自动删除**
- "加入待制作"暂存机制（避免用户每次重新生成 Preview）

### 5.7 后端接口契约（Phase 2 实现合同）
Phase 1 PRD 必须冻结：
- `PreviewProvider` 接口签名 + 错误码 + 重试策略 + fallback 顺序
- `PatternBuilder` 输入输出 schema（与 Task H 的色卡 schema 对齐）
- 用户作品集数据模型（含 ADR-009 保存策略）

---

## 6. 已知未决事项（带回 Phase 1 PRD 或单独评估）

| 事项 | 类型 | Phase 1 PRD 是否需要 | 备注 |
|------|------|--------------------|------|
| 域名（推荐 `pindou.cn`） | 决策 | 不需要 | 用户去查可用性 |
| 上海 8C16G 20M 服务器部署方案 | 工程 | 不需要 | Phase 2 起步前让 Codex 写 `07_ops/deployment.md` |
| 国内 ICP 备案启动时机 | 流程 | 不需要 | Phase 2 末启动（FUTURE_WORK 第 2 条） |
| 微信小程序"加客服扫码付"具体实现 | PRD 必须覆盖 | **是** | 替代官方微信支付 |
| 流量主激励视频接入 | PRD 可选 | 可延后 | UV ≥ 1000 后才能开通 |
| 5 人主观投票 | 已取消 | — | ADR-005a 修订删除 |
| 国产 provider 应急 | 已 ADR-007 接受不做 | — | 监控触发条件 |

---

## 7. Phase 0 出口自检

| 项 | 状态 | 备注 |
|----|------|------|
| Skills 盘点 | ✅ | `00_meta/skills_inventory.md` |
| API/Key 盘点 | ✅ | `00_meta/api_inventory.md`（gpt-image-2 反代主通道 + 文本反代备用） |
| 6 份调研报告（A-F） | ✅ | A/B/C/D/E/F 全部 completed |
| 任务 C 量化输出实际样本 | ✅ | 120 张样本（合成图） + 私有素材实验摘要 |
| 9 个 ADR 落档 | ✅ | DECISION_LOG.md 索引 |
| `data_sources.md` 留痕 | ✅ | 由 Codex 在各任务追加 |
| Commit message 符合规范 | ✅ | `docs(phase0-...)` 前缀 |
| Phase 0 综合简报 | ✅ | 本文件 |
| **Task H（新增，Phase 1 启动前必须完成）** | 🟡 进行中 | 用户已派 Codex 启动 |

**Phase 0 评审通过条件**：
- Task H 完成 → Phase 0 真正结案 → 合并 phase0 分支到 main → 启动 Phase 1 PRD

---

## 8. 给 Phase 1 PRD 撰写者的备忘

如果你（Codex / Claude / 用户）即将开始 Phase 1 PRD：

**必读**（按顺序）：
1. 本文件
2. PROJECT_CHARTER.md
3. 全部 9 个 ADR（特别 ADR-005a 修订版、ADR-008、ADR-009）
4. FUTURE_WORK.md（8 条）
5. Task C 的 `perler_bead_domain_notes.md`（拼豆领域知识，PRD 大量引用）
6. Task B 的 `algorithms.md`（PatternBuilder 算法基线）
7. Task F 的 `compliance_checklist.md`（Phase 1 PRD 用户协议 / 隐私政策起草必读）
8. Task H 输出（Task H 完成后）

**PRD 撰写顺序建议**：
1. 用户画像 + 用户路径（先把用户旅程画清楚）
2. 风格 + 尺寸预设清单 + UX 草图（不要落到具体设计稿）
3. `PreviewProvider` 接口契约（含 fallback chain 配置）
4. `PatternBuilder` 接口契约（含 palette 数据契约对齐 Task H）
5. 数据模型（用户、作品、订单、私人素材保存策略遵循 ADR-009）
6. 用户协议 + 隐私政策草案
7. Phase 2 后端实现的非功能性需求（性能、可用性、监控）

**评审建议**：
PRD v1 强烈建议带回 chat 端 Claude 评审。PRD 是 Phase 2 后端开发的合同，错了影响范围比 Phase 0 大一个量级。

---

**Phase 0 结。**
