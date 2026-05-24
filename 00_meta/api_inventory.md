# API / Key 盘点

> **盘点日期**：2026-05-24
> **盘点人**：Claude Code
> **重要安全规则**：本文件只列**服务名 + 用途 + 状态**。**绝对不写 key 本体**，key 走 `.env`（已在 `.gitignore`）。
> **数据源**：用户桌面 `apisell/` 目录下的 `私人api.md`、`技术文档.md` 等。

---

## 一、已具备的 API 资源

### 1. 反代网关（OpenAI 兼容协议）
- **服务名**：xiaochisaas 私人反代
- **入口**：`https://api2.xiaochisaas.com`
- **协议**：OpenAI 兼容（chat completions / image generation 等）
- **用途**：本项目 AI 风格化 PoC 主入口（ADR-005）
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
| **gpt-image-1 直接访问**（反代列表里没有，只有 `gemini-3-pro-image`） | ADR-005 主推路线 Q版/宠物/通用卡通 | **高** | Phase 0 任务 C PoC |
| **微信小程序 AppID + AppSecret** | 小程序开发、登录、分享 | 高 | Phase 2 后端 / Phase 3 提审 |
| **微信支付商户号 + 支付密钥** | 付费购买 / 月卡 | 中高 | Phase 3 提审前 |
| **对象存储**（阿里 OSS / 腾讯 COS / 七牛云任一） | 用户上传原图 + 生成图纸存储 | 高 | Phase 2 后端 MVP |
| **图片审核服务**（绿网 / 阿里内容安全等） | 上传图过滤违禁 | 中 | Phase 3 提审前 |
| **AutoDL 或同类 GPU 租赁账号** | ADR-005 写实人像路线自部署 ComfyUI | 中 | Phase 0 任务 C PoC（方案 3） |

---

## 三、关键不确定项 — 请用户确认

1. **gpt-image-1 是否真的可用？**
   反代模型列表里只有 `gemini-3-pro-image`，没有 `gpt-image-1`。
   ADR-005 主路线（Q 版 / 宠物 / 通用卡通）依赖 gpt-image-1。
   是否：
   - (a) 反代另有暗藏的 gpt-image-1 通道？
   - (b) 用 `gemini-3-pro-image` 替代 gpt-image-1 做 PoC？
   - (c) 走第三方反代（如 OpenRouter）单独接 gpt-image-1？

2. **写实人像主路线（SD + IPAdapter + ControlNet）的 GPU 来源**？
   - (a) AutoDL 租 4090（按小时计费，开发期可控）？
   - (b) 用户已有本地显卡？
   - (c) 直接走 ComfyUI 云托管（如 RunComfy / RunPod）？

3. **小程序主体**：以个人名义申请，还是用户已有公司主体？（影响类目申请、AIGC 备案路径）

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
