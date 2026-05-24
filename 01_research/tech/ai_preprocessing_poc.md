# Task C — AI 预处理纯 API PoC

> 状态：blocked（2026-05-24）  
> 原因：本地 `.env` 未提供 `XIAOCHI_GPT_API_KEY`，也未提供火山 / 通义 API key；无法真实调用 `gpt-image-2`，也无法产出 ADR-005a 要求的量化输出样本和 5 人主观投票数据。  
> 已完成：PoC runner、15 张非真实合成输入、prompt 文档、投票表模板、阻塞问题记录。

## 当前可交付物

| 文件 / 目录 | 内容 |
|-------------|------|
| `01_research/tech/poc_runner.py` | P1 OpenAI-compatible image edit runner；只从 `.env` 读 key；生成后接 Task B 推荐量化组合 |
| `01_research/tech/prompts.md` | 四个风格预设 Prompt 草案 |
| `01_research/tech/test_inputs_poc/` | 15 张非真实合成测试图：5 人像、5 宠物、5 情侣合成图 |
| `01_research/tech/subjective_vote_template.csv` | 5 位志愿者评分模板 |
| `00_meta/codex_briefs/_questions_for_user.md` | 需要用户补 key / 决策的问题 |

## Provider 状态

| Provider | 需要环境变量 | 当前状态 | 处理 |
|----------|--------------|----------|------|
| P1 `gpt-image-2` | `XIAOCHI_GPT_API_KEY` | 缺失 | blocked；补 key 后运行 |
| P2 火山即梦 | `VOLC_ACCESS_KEY`, `VOLC_SECRET_KEY` | 缺失 | 暂跳过，报告中标注 |
| P3 通义万相 | `ALIYUN_DASHSCOPE_API_KEY` | 缺失 | 暂跳过，报告中标注 |

## 复现 / 续跑

检查 provider 可用性：

```bash
python 01_research/tech/poc_runner.py status
```

生成非真实测试输入：

```bash
python 01_research/tech/poc_runner.py make-inputs
```

补充 `XIAOCHI_GPT_API_KEY` 后跑 P1：

```bash
python 01_research/tech/poc_runner.py run-p1
```

调试时可先跑 1 张：

```bash
python 01_research/tech/poc_runner.py run-p1 --limit 1
```

## 验收缺口

- [ ] 至少 P1 x 4 风格真实 API 调用成功。
- [ ] 写实人像 + 情侣量化输出图达到至少 15 张。
- [ ] 5 位志愿者主观投票完成，计算平均分与 `>=3` 通过率。
- [ ] 成本 / 延迟 / 稳定性表格：至少 20 次延迟样本，50 次成功率样本。
- [ ] 产出每个风格预设最优 Provider + Prompt 组合。

## 当前判断

Task B 已给出量化基线：**K-means + CIEDE2000 + 无抖动**。Task C 续跑时，所有 AI 生成图应先统一进入这个量化组合，再给志愿者看最终 100x100 x 24 色输出图。

## 风险记录

- P1 反代接口的 `images/edits` 兼容性需用 key 实测确认；如只支持 `images/generations` 或其他路径，需要调整 runner。
- 火山 / 通义 provider 缺失，不影响 P1 最小 PoC，但会影响“多 provider fallback”结论。
- 合成测试图不等于真实用户照片；正式主观投票建议用户提供授权素材或用 AI 假人脸，真实人像 commit 前必须再次确认。
