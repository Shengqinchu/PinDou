# ADR-005a: 转向 Q 版 FinishedPreview 路线 / GPU 决策路径关闭

- **状态**: Accepted（2026-05-24 修订，覆盖原 PoC 投票验收方案）
- **日期**: 2026-05-24（首版）/ 2026-05-24（修订）
- **决策者**: 用户 + Claude Code
- **影响范围**: ADR-005、Task C 验收、FUTURE_WORK 第 1 条、Phase 1 PRD 起点
- **修订记录**: 取代首版"5 人主观投票决定 GPU 触发"的方案

## 背景
首版 ADR-005a 设计了 "5 人志愿者主观投票 + 量化输出图 + ID 保持评分 + GPU 触发门槛" 的验收路径，目的是用数据决定是否上 GPU。

用户在私有素材实验后做出两个关键判断（依据：`01_research/tech/perler_bead_domain_notes.md` + Codex handoff）：
1. **拼豆产品的最优形态是"Q 版 FinishedPreview → 程序化 PatternSheet"**，不是"写实人像 + 量化"
2. **写实人像路线本身在拼豆量化场景里不是用户最想要的**（用户买拼豆是为了好看 + 可爱 + 能制作，不是为了"像照片"）
3. 既然产品方向不再追求写实保持，**GPU 触发条件失去意义**——上 GPU 是为了 ID 保持，Q 版路线不依赖严格 ID 保持

用户同时决定**不组织 5 人主观投票**：私有素材已经验证 Q 版 + 程序化的产品形态可行，志愿者投票成本高、价值低。

## 决策

### 1. 主路线确定：Q 版 FinishedPreview
- 四个风格预设的 AI 风格化全部走 "**Q 版 / chibi / 卡通化**" 路径
- 写实人像不再是 Phase 1 主路线，降级为 Phase 2+ 可选功能（"忠于原貌"模式）
- 所有 Provider（gpt-image-2 主）的 prompt 工程按 Q 版优化（参考 `01_research/tech/prompts.md` 拼豆约束）

### 2. 关闭 GPU 决策路径
- 不再保留"PoC 投票 → 触发 GPU"的判断逻辑
- FUTURE_WORK 第 1 条降级：写实路线降到 Phase 2+ 可选功能，GPU 不作为产品 blocker
- 如 Phase 2+ 用户要"忠于原貌"模式，再单独评估技术路径（届时国内 / 云 GPU 可选项也会变化）

### 3. 删除 5 人主观投票验收
- 删除"5 张人像 + 5 张情侣 × 5 志愿者打分 + 平均分门槛"全套
- 不再阻塞 Task C completed 状态

### 4. 新验收（替代）
Task C 完成度判断改为：
- ✅ Provider 接通 + 至少 40 条 P1 调用成功（已达成）
- ✅ 拼豆领域 prompt 工程文档化（已达成，`prompts.md`）
- ✅ Q 版 FinishedPreview 在私有素材测试中产出可用样本（用户已确认）
- ✅ Phase 1 `PreviewProvider` / `PatternBuilder` 接口建议落档（ADR-008）

## 理由
- 产品方向转向后，原投票测试对象（写实保持）变得无意义
- 用户已通过私有素材完成产品形态验证，等效于"小规模 1 人投票通过"
- 减少 Phase 0 收尾时间，把工时投入 Phase 1 PRD

## 后果

### 正面
- Phase 0 直接结案，不卡投票流程
- Phase 1 PRD 起点清晰：Q 版 + FinishedPreview + PatternSheet 拆分
- Provider 抽象层简化（不需要 GPU 后端实现）

### 负面 / 风险
- 写实人像用户群（如老人 / 长辈纪念照场景）暂时不服务
- 如 Phase 2+ 要补写实功能，那时 GPU 决策必须重做（这是已知 trade-off）

## 备选方案
- **保留首版投票流程**：被否，产品方向已转，投票对象失效
- **写实保持作为 Phase 1 副线**：被否，资源分散，Q 版主路线还没跑稳就分叉

## 关联
- 修订 ADR-005（主表："写实人像 Provider 1 主推" 该项后续与 ADR-008 一并整合）
- 修订 FUTURE_WORK 第 1 条（GPU 触发条件降级）
- 关联 ADR-008（FinishedPreview / PatternSheet 拆分）
- 关闭 Task C 主观投票阻塞
