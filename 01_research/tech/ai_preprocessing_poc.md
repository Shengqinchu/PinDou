# Task C — AI 预处理纯 API PoC

> 状态：completed (Codex @ 2026-05-24) — P1 PoC complete，待用户线下组织 5 位志愿者主观投票。  
> 注意：投票数据出来之前，不写 ADR-005a “达标”结论。  
> 已完成：P1 `gpt-image-2` 真实 API 调用、40 组 AI 输出 + 量化输出、投票模板、可续跑 runner。

## 当前可交付物

| 文件 / 目录 | 内容 |
|-------------|------|
| `01_research/tech/poc_runner.py` | P1 OpenAI-compatible image edit runner；只从 `.env` 读 key；可跳过已生成样本续跑 |
| `01_research/tech/prompts.md` | 四个风格预设 Prompt 草案 |
| `01_research/tech/test_inputs_poc/` | 15 张非真实合成测试图：5 人像、5 宠物、5 情侣合成图 |
| `01_research/tech/poc_samples/` | P1 原图 / AI 生成图 / 100x100 量化输出图 |
| `01_research/tech/poc_results.csv` | 40 条 P1 调用结果、延迟与量化指标 |
| `01_research/tech/subjective_vote_template.csv` | 5 位志愿者 x 40 样本 = 200 行评分模板 |

## Provider 状态

| Provider | 需要环境变量 | 当前状态 | 处理 |
|----------|--------------|----------|------|
| P1 `gpt-image-2` | `XIAOCHI_GPT_API_KEY` | 已跑通 40/40 | 可作为 Phase 1 API PoC 主路径 |
| P2 火山即梦 | `VOLC_ACCESS_KEY`, `VOLC_SECRET_KEY` | 本阶段跳过 | Phase 2 备选 provider 评估 |
| P3 通义万相 | `ALIYUN_DASHSCOPE_API_KEY` | 本阶段跳过 | Phase 2 备选 provider 评估 |

## P1 样本覆盖

| 风格组 | 样本数 | 输入范围 |
|--------|--------|----------|
| `realistic_portrait` | 10 | 5 人像 + 5 情侣 |
| `chibi_portrait` | 10 | 5 人像 + 5 情侣 |
| `pet` | 5 | 5 宠物 |
| `cartoon` | 15 | 5 人像 + 5 情侣 + 5 宠物 |

机器校验结果：

- API 成功率：40/40（本轮未观察到 HTTP 或解析失败）。
- 图片完整性：40 张原图、40 张 AI 图、40 张量化图均可打开；量化图尺寸均为 100x100。
- 写实人像 + 情侣量化输出：20 张，满足“>=15 张量化输出图”前置条件。

## 成本 / 延迟 / 稳定性

| 维度 | 样本数 | 结果 |
|------|--------|------|
| 成本 | 40 | 当前反代 API 响应未返回单次计费字段；需用管理后台 / 账单侧补充核算 |
| 延迟 | 40 | 平均 39.63 s；P50 33.13 s；P95 59.83 s |
| 稳定性 | 40 | 成功 40，失败 0；本轮观测成功率 100% |

## 量化指标

| 风格组 | count | 平均 CIEDE2000 | 平均 SSIM | 平均 PSNR |
|--------|-------|----------------|-----------|-----------|
| `cartoon` | 15 | 20.72 | 0.44 | 10.61 |
| `chibi_portrait` | 10 | 23.09 | 0.41 | 10.08 |
| `pet` | 5 | 13.13 | 0.52 | 13.52 |
| `realistic_portrait` | 10 | 19.84 | 0.51 | 11.18 |

说明：这些客观指标只衡量量化图与原图的颜色 / 结构相似性，不能替代 ADR-005a 的身份保持主观投票。

## 复现 / 续跑

检查 provider 可用性：

```bash
python 01_research/tech/poc_runner.py status
```

生成非真实测试输入：

```bash
python 01_research/tech/poc_runner.py make-inputs
```

运行 / 续跑 P1：

```bash
python 01_research/tech/poc_runner.py run-p1
```

调试时可先跑 1 张输入：

```bash
python 01_research/tech/poc_runner.py run-p1 --limit 1
```

Runner 会读取 `poc_results.csv` 并跳过已有完整样本，避免重复消耗 API。

## 主观投票阶段

- [x] P1 x 4 风格真实 API 调用成功。
- [x] 写实人像 + 情侣量化输出图达到至少 15 张。
- [x] 至少 20 次延迟样本。
- [x] `subjective_vote_template.csv` 已生成，供 5 位志愿者线下评分。
- [ ] 用户线下组织 5 位志愿者主观投票。
- [ ] 投票完成后，汇总平均分与 `>=3` 通过率，再判断 ADR-005a 是否达标。

## 当前判断

Task B 已给出量化基线：**K-means + CIEDE2000 + 无抖动**。Task C 已把 P1 的 AI 生成图统一进入该组合，产出最终 100x100 x 24 色量化图。是否“像本人”和是否“值得付费”仍必须看 `subjective_vote_template.csv` 的 5 人评分结果。

Phase 1 设计上可以先按 P1 打通 `StylizationProvider` 抽象：

- 输入：原图、风格预设、输出尺寸、目标色卡。
- 输出：AI 原图 URL / 本地路径、量化图路径、provider、style、latency、错误码。
- 重试：网络 / 5xx 至少 2 次指数退避；审核拒绝不重试，提示换图或换风格。
- Fallback：Phase 1 仅实现 P1 主路径 + 同 provider 内 prompt fallback；P2/P3 留作 Phase 2 备选 provider 评估。
- 评估：所有人像付费路径上线前必须要求量化图主观投票过线。

## 风险记录

- 当前测试输入均为非真实合成图；正式主观投票建议用户提供授权素材或用 AI 假人脸，真实人像 commit 前必须再次确认。
- P1 单次延迟接近 30-60 秒，用户体验需要排队态、异步任务与失败重试。
- 反代未返回成本字段，定价模型仍需要管理后台 / 账单侧核算。
- P2/P3 本阶段确认跳过；供应商稳定性、审核策略、成本比较与 fallback 设计留到 Phase 2。
