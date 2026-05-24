# Task C — AI 预处理纯 API PoC（核心任务）

**Status**: blocked - 缺少 P1/P2/P3 API key，无法真实调用 gpt-image-2 / 即梦 / 通义；已产出 [PoC runner](../../01_research/tech/poc_runner.py), [prompts](../../01_research/tech/prompts.md), [blocked report](../../01_research/tech/ai_preprocessing_poc.md)
**Owner**: Codex
**Priority**: **最高**
**Estimated**: 3-5 天
**依赖**: 任务 D 色卡数据库 + 任务 B 量化算法

---

## ⚠️ 重要：本任务方案已根据 ADR-005a 调整

**变化点**（不要按 ADR-005 原方案做）：
- ❌ 不上 GPU、不自部署 SD、不用 IPAdapter / ControlNet
- ✅ 全部走反代 API：`gpt-image-2` + 即梦 + 通义万相
- ✅ **PoC 验收用量化输出图，不用 AI 生成原图**
- ✅ ID 保持评估用 5 位志愿者主观投票，门槛 ≥ 3.0/5

---

## 背景
ADR-003 的付费转化假设：AI 预处理后的拼豆图纸要明显比纯量化好看。ADR-005a 的决策：拼豆量化会糊掉精细差异，所以测试必须看**量化后的最终输出**像不像本人，不是 AI 生成原图。

本任务的成败直接决定：
- 是否需要 FUTURE_WORK 第 1 条触发（上 GPU）
- ADR-003 定价方案是否成立
- Phase 1 PRD 怎么写 `StylizationProvider` 接口

## 目标
验证"纯 API 路线 + 智能量化"能否产出"明显比纯量化好 + 写实人像看得出像本人"的拼豆图纸。

## 三个 API Provider

### Provider 1：xiaochisaascn GPT 反代（主）
- base_url: `https://gpt.xiaochisaascn.org/v1`
- key 环境变量：`XIAOCHI_GPT_API_KEY`
- 主用模型：`gpt-image-2`
- 调用协议：OpenAI 原生 image generation API

### Provider 2：火山即梦（备）
- **API 待补**，用户尚未提供，启动前先和用户确认 key
- 如未补齐，本 provider 跳过，PoC 用 P1 + P3 跑
- key 环境变量（待定）：`VOLC_ACCESS_KEY` / `VOLC_SECRET_KEY`

### Provider 3：阿里通义万相（备）
- **API 待补**，用户尚未提供
- key 环境变量：`ALIYUN_DASHSCOPE_API_KEY`
- 如未补齐，本 provider 跳过

**最低可行**：Provider 1 必须跑通；P2/P3 缺失不阻塞任务启动，但要在报告里写明缺失原因。

---

## 测试集
- **5 张人像**（必须包含正脸、侧脸、戴眼镜各一张）
- **5 张宠物**（猫 / 狗 / 不同毛色）
- **5 张情侣合影**（两个人脸出现在同一张图）

**素材规则**：
- 用户提供 / 公开素材（CC0 或公共领域）/ Codex 自行用 AI 生成假人脸（如 `thispersondoesnotexist.com`）
- **禁止使用任何真实可识别的非本人/非授权人物照片**
- 测试集存到 `01_research/tech/test_inputs_poc/`，**禁止 commit 真实人像**，commit 之前问用户

## 四个风格预设 × 3 个 Provider = 12 组测试

| 风格预设 | Provider 1 (gpt-image-2) | Provider 2 (即梦) | Provider 3 (通义) |
|----------|--------------------------|-------------------|-------------------|
| 写实人像 | Prompt A | Prompt A' | Prompt A'' |
| Q 版人像 | Prompt B | Prompt B' | Prompt B'' |
| 宠物 | Prompt C | Prompt C' | Prompt C'' |
| 通用卡通 | Prompt D | Prompt D' | Prompt D'' |

## Prompt 工程（强约束 vs 弱约束）

### 写实人像 Prompt（强约束模板）
```
preserve exact facial features, identity, expression, and proportions of the input person.
only change the rendering style to N-bit pixel art suitable for perler bead patterns.
do not alter face shape, eye spacing, nose, mouth shape, or skin tone.
output: front-facing, plain background, 1024x1024.
```
**关键**：测试不同 N 值（8-bit / 16-bit / 24-bit）对量化输出的影响。

### Q 版人像 Prompt（弱约束）
```
chibi / cute cartoon version of the input person, big head, simplified features,
N-bit pixel art style. preserve hair color, skin tone, and general identity hints,
but allow stylized exaggeration. plain background, 1024x1024.
```

### 宠物 / 卡通 Prompt
按需调，参考写实和 Q 版的中间态。

---

## 完整工作流

```
原图（1024×1024）
  → [Provider X + 风格预设 Y 的 prompt]
  → AI 生成图（1024×1024）
  → [任务 B 的最佳量化组合，用 MARD 色卡]
  → 量化输出图（100×100 × 24 色）
  → 主观投票
```

**每组保存 3 张图**：原图 / AI 生成图 / 量化输出图（命名：`P{1-3}_{portrait/qversion/pet/cartoon}_{seq}_{stage}.png`）

---

## 验收：ID 保持率主观投票（写实人像 + 情侣）

### 投票流程
1. 找 5 位志愿者（用户朋友 / 同学 / 小红书读者等），**不能事先看过原图**
2. 给志愿者看：原图 + 5 张量化输出图（不同 provider × 风格）
3. 每张打分：**1 = 完全不像，5 = 非常像**
4. 计算每个 provider × 风格的：平均分 + ≥3 分通过率

### 写实人像验收门槛（ADR-005a）
- **平均分 ≥ 3.0**：API 路线达标，关闭 ADR-005a，永久放弃 GPU
- **平均分 2.0-2.9**：组合调优后复测（换 prompt、换 provider、加抖动）
- **平均分 < 2.0**：触发 FUTURE_WORK 第 1 条，写实人像引入 GPU 路线

### Q 版 / 宠物 / 卡通验收门槛（较松）
- 平均分 ≥ 2.5 即可
- 重点看"用户会不会觉得'值得为这个付 9.9 元'"——附加一项主观题
- 与同图的"纯量化"对比图一起给志愿者看，问"哪张你愿意花钱做出来"

---

## 对比维度（必须量化或样本对照）
- **身份保持度**（主观评分 + 关键点距离，若可用）
- **像素感 / 像素风格还原度**
- **色彩饱和度与原图一致性**（CIEDE2000 平均色差）
- **单次成本**（接口费 / token）
- **延迟**（P50 / P95，至少 20 次调用样本）
- **稳定性**（成功率，至少 50 次调用样本）

---

## 输出位置
- 主报告：`01_research/tech/ai_preprocessing_poc.md`
- 测试输入：`01_research/tech/test_inputs_poc/`
- AI 生成 / 量化输出样本：`01_research/tech/poc_samples/`
  - 子目录按 `P{1-3}_{风格}/` 组织
- Prompt 工程文档：`01_research/tech/prompts.md`
- 调用代码：`01_research/tech/poc_runner.py`（配置驱动 + 走 `.env`）

## 验收标准
- [ ] 至少 12 组测试有完整数据（如 P2/P3 缺失，至少 4 组：P1 × 4 风格）
- [ ] 写实人像 + 情侣 ≥ 15 张量化输出图，5 人主观投票完整数据表
- [ ] 平均分超过 / 未超过 3.0 的结论明确写出
- [ ] 每个 Provider 的成本 / 延迟 / 稳定性表格
- [ ] 推荐：每个风格预设最优的 Provider + Prompt 组合
- [ ] 风险清单：API 限流 / 审核拒绝 / 偏见行为 / 边缘 case 记录
- [ ] 给 Phase 1 `StylizationProvider` 接口设计的具体建议（输入 / 输出 / 重试 / fallback）

## 不要做
- ❌ 不要自部署 SD / ComfyUI（ADR-005a）
- ❌ 不要用 ControlNet / IPAdapter（API 不支持）
- ❌ 不要把真实人像 commit 到 git
- ❌ 不要为了赶进度跳过主观投票（**投票是核心验收**）
