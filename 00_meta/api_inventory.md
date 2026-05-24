# API / Key 盘点

> **盘点日期**：2026-05-24
> **盘点人**：Claude Code
> **重要安全规则**：本文件只列**服务名 + 用途 + 状态**。**绝对不写 key 本体**，key 走 `.env`（已在 `.gitignore`）。
> **数据源**：用户桌面 `apisell/` 目录下的 `私人api.md`、`技术文档.md` 等。

---

## 一、已具备的 API 资源

### 1. 反代网关 — GPT 图像主通道（OpenAI 兼容协议）
- **服务名**：xiaochisaascn GPT 反代
- **入口（base_url）**：`https://gpt.xiaochisaascn.org/v1`
- **管理页**：`https://gpt.xiaochisaascn.org/management.html`
- **环境变量**：`XIAOCHI_GPT_API_KEY`（key 不入档，已在 `.env.example` 列出变量名）
- **协议**：OpenAI 原生（`/v1` 路径）
- **可用模型**：

| 模型 | 用途映射（PinDou） |
|------|-------------------|
| `gpt-image-2` | **图像生成主路线**（ADR-005 + ADR-005a，写实/Q版/宠物/通用卡通统一通道）|
| `gpt-5.2` / `gpt-5.3-codex` / `gpt-5.3-codex-spark` | 备选文本（不计划用） |
| `gpt-5.4` / `gpt-5.4-mini` | 备选 |
| `gpt-5.5` / `gpt-5.5-high` / `gpt-5.5-low` / `gpt-5.5-xhigh` / `gpt-5.5-xhigh-fast` | 备选高质量 / 复杂推理 |
| `codex-auto-review` | 代码评审，Phase 2 后端 PR 可用 |
| `my-gpt` | 备选 |

- **重要说明**：原 ADR-005 写"反代 gpt-image-1"，实际可用版本为 **gpt-image-2**（更新版，ID 保持据传更强，待 PoC 实测）
- **用途**：PinDou AI 风格化主图像通道（ADR-005 / 005a）

### 2. 反代网关 — 文本通道（OpenAI 兼容协议）
- **服务名**：xiaochisaas 私人反代
- **入口**：`https://api2.xiaochisaas.com`
- **环境变量**：`XIAOCHI_TEXT_API_KEY`
- **协议**：OpenAI 兼容（chat completions / image generation 等）
- **用途**：文本辅助任务（审核、文案、PRD 评审）；图像生成备选（`gemini-3-pro-image`）
- **可用模型清单**（来自 `apisell/私人api.md`）：

| 模型 | 可用性 | 用途映射（PinDou） |
|------|--------|-------------------|
| `gemini-3-flash` | ✅ | 备用语言模型 / 文案生成 |
| `gemini-3.1-pro-high` | ✅ | 高质量文本任务（PRD 评审、Prompt 调优） |
| `gemini-3.1-pro-low` | ✅ | 低成本文本任务 |
| `gemini-3-pro-image` | ✅ | **图像生成主候选**（可能替代 gpt-image-1） |
| `claude-sonnet-4-6` | ✅ | 后端业务文本（审核 / 摘要） |
| `claude-opus-4-6-thinking` | ⚠️ 未测试（账号支持） | 复杂推理 |
| `gemini-2.5-pro` | ⚠️ 未测试 | 备选 |
| `gemini-2.5-flash` | ⚠️ 未测试 | 备选 |

- **成本**：用户已自备工具，研发阶段视为可忽略
- **稳定性风险**：反代依赖 Cloudflare Tunnel + Mac Mini 多账号 chix2-chix8，重启需手动恢复（详见 `apisell/私人api.md`）
- **合规风险**：用于生产存在 AIGC 备案合规风险，Phase 2 备案或切国产 provider（ADR-005）

### 2. 用户已有的其他基础设施（非 PinDou 直接消费，但可借鉴）
- xiaochisaas 自营 API 售卖业务（NewAPI 网关 + 余额查询 + 抽奖系统）
- 日本腾讯云服务器（`43.167.226.239`，4核8GB）— **可作为 PinDou 后端候选托管点**

---

## 二、❗ 缺失项（需用户补齐后才能启动 Codex 任务 C / 后续 Phase）

| 服务 | 用途 | 优先级 | 必需阶段 |
|------|------|--------|----------|
| **火山引擎 API**（即梦图像生成、Doubao） | ADR-005 备选 provider；国产合规通道候选 | **高** | Phase 0 任务 C PoC |
| **阿里通义 API**（万相图像生成、通义千问） | ADR-005 备选 provider；国产合规通道候选 | **高** | Phase 0 任务 C PoC |
| **SiliconFlow API** | 调用开源模型（SD / FLUX 等）的低成本通道 | 中 | Phase 0 任务 C PoC（可选） |
| **微信小程序 AppID + AppSecret** | 小程序开发、登录、分享 | 高 | Phase 2 后端 / Phase 3 提审 |
| **微信支付商户号 + 支付密钥** | 付费购买 / 月卡 | 中高 | Phase 3 提审前 |
| **图片审核服务**（绿网 / 阿里内容安全等） | 上传图过滤违禁 | 中 | Phase 3 提审前 |

> **已决策不需要的**：
> - ❌ **AutoDL / GPU**：纯 API 路线（ADR-005a），不上 GPU
> - ❌ **对象存储**：MVP 期用日本服务器本地磁盘 + Nginx 静态反代，触发条件见 FUTURE_WORK.md 第 3 条

---

## 三、已确认事项

1. **图像生成主模型**：`gpt-image-2`（不是 gpt-image-1），通过 `gpt.xiaochisaascn.org/v1` 反代访问。ID 保持效果待 PoC 实测，验收门槛见 ADR-005a。
2. **后端托管**：MVP 期日本腾讯云服务器（`43.167.226.239`），跨境合规风险记录在 FUTURE_WORK.md 第 2 条。
3. **写实人像路线**：先走纯 API，不上 GPU。PoC 验收用量化输出图主观投票（详见 ADR-005a）。
4. **Key 安全**：用户决定不轮换当前 gpt 反代 key。本仓库 `.env.example` 仅列变量名 `XIAOCHI_GPT_API_KEY`，key 本体走 `.env`（已 gitignore）。

## 四、待用户后续确认

（暂无）

**已确认的主体决策**：小程序以个人主体注册（ADR-006），后续升级触发条件见 FUTURE_WORK.md 第 6 条。

---

## 四、安全提醒
- 旧 key `sk-9a0b58014b9f4b35bd9849a6bdfc1d08` 已泄露，禁止使用（参见 `apisell/api_key_audit.md`）
- 新 key 通过 `.env` 注入，**永远不要 commit**
- `.env.example` 仅列变量名，不列值

---

## 五、更新记录
| 日期 | 变更 | 操作人 |
|------|------|--------|
| 2026-05-24 | 初版盘点 | Claude Code |
