# Codex 启动 Prompt 模板

> 用户复制下面任一 prompt 给 Codex，启动调研工作。
> Prompt 设计哲学：Codex 自己读 README + brief 比我们在 prompt 里复述效率高。

---

## 版本 A：总启动 Prompt（一个 session 跑所有任务，串行）

```
你被分配为 PinDou 项目的 Phase 0 调研执行者。

项目根目录：C:\Users\123\Desktop\PinDou
你的全部任务说明 + 工作规则 + 强约束都在：
  00_meta/codex_briefs/README.md

执行流程：
1. cd 到项目根目录
2. git status 确认在 phase0 分支
3. 通读 README.md 列出的全部前置阅读（不读不许开工）
4. 从任务 D 开始（D 是 B 和 C 的依赖）
5. 任务文件顶部 Status 改 in_progress (Codex @ 日期)；完成后改 completed + 链接产出文件
6. 每个任务完成单独 commit：docs(phase0-task-X): 简短描述
7. 遇到要决策的疑问先停下来，写到 codex_briefs/_questions_for_user.md（如不存在则创建），不要瞎拍板

绝对红线：
- 不在代码 / 文档 / commit 中写 API key 本体；走 .env（已 gitignore，模板见 .env.example）
- 任务 C 严格按 ADR-005a 做：纯 API 路线、不用 GPU、量化输出主观投票验收
- 真实人像测试图 commit 前问用户
- 任务完成 ≠ 合并到 main；留在 phase0 分支等用户带回 chat 端 Claude 评审

第一步：cd 进项目，git status，然后读 README.md。
```

---

## 版本 B：单任务 Prompt（每个任务开独立 Codex session，并行更快）

```
PinDou Phase 0 任务认领。

项目根目录：C:\Users\123\Desktop\PinDou（分支 phase0）
你的任务：task_<X>   ← 把 <X> 换成 A / B / C / D / E / F / G

请先读：
  00_meta/codex_briefs/README.md             ← 工作规则
  00_meta/codex_briefs/task_<X>_*.md         ← 你的任务
  00_meta/PROJECT_CHARTER.md
  04_architecture/ADRs/ 全部 6 个 ADR
  00_meta/FUTURE_WORK.md
  00_meta/api_inventory.md

读完把 task_<X>_*.md 顶部 Status 改 in_progress，开始干活。

绝对红线（详见 README.md "通用规则"）：
- 不写 API key 本体；走 .env
- 任务 C 必须按 ADR-005a（不用 GPU、量化输出主观投票）
- 真实人像 commit 前问用户
- 完成后单独 commit：docs(phase0-task-<X>): 简短描述
- 疑问写到 codex_briefs/_questions_for_user.md

第一步：cd C:\Users\123\Desktop\PinDou && git status
```

---

## 推荐用法

### 场景 1：你只有一个 Codex 实例
用**版本 A**。Codex 会按推荐顺序 D → B → C → A → E → F → G 串行跑完。

### 场景 2：你有多个 Codex 实例 / 想并行
- **先**用版本 B 派一个 Codex 跑 task_D（必须先跑完，B/C 依赖它）
- task_D 完成后，**并行**派 4 个 Codex 分别跑 task_B、task_C、task_F、task_E
- 剩下 task_A、task_G 任何空闲实例顺手跑

### 场景 3：Codex 卡住了
检查 `codex_briefs/_questions_for_user.md`，看他提了什么疑问。

---

## 进度同步约定（Codex 必须遵守）

每个任务 brief 顶部都有：
```
**Status**: pending → in_progress (Codex @ YYYY-MM-DD) → completed (Codex @ YYYY-MM-DD)
```

我（Claude Code）会通过 `git log` + 这个 Status 字段判断进度，不需要 Codex 单独汇报。

---

## 评审流程

Codex 提交所有任务后：
1. Claude Code 检查 Phase 0 出口标准（README 末尾清单）
2. Claude Code 撰写 `00_meta/phase0_summary.md`（5-10 页综合简报）
3. 用户带 `phase0_summary.md` 回 chat 端找 Claude 评审
4. 评审通过 → 合并 phase0 分支到 main，进入 Phase 1
5. 评审有意见 → Codex 按意见修订，重新走流程
