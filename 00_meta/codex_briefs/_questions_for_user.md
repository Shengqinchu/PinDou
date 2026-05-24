# Questions For User

## 2026-05-24 — Task C API PoC follow-up

已处理：

- P1 `gpt-image-2` key 已通过本地 `.env` 补齐。
- P1 真实 API 已跑通 40/40 样本，结果见 `01_research/tech/poc_results.csv`。
- 量化输出图已生成，投票模板见 `01_research/tech/subjective_vote_template.csv`。

仍需用户决策：

1. 是否本阶段跳过火山即梦 / 阿里通义万相，只保留 P1 结论？如不跳过，请补充 `VOLC_ACCESS_KEY` / `VOLC_SECRET_KEY` / `ALIYUN_DASHSCOPE_API_KEY` 到 `.env`。
2. Task C 的 5 位志愿者主观投票是否由用户线下组织？如果是，请使用 `subjective_vote_template.csv` 填分后再让 Codex 汇总平均分与通过率。
3. 是否允许继续消耗 P1 API 再补 10 次调用，把稳定性样本从 40/50 补齐到 brief 要求的 50/50？
