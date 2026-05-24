# Task A — 现有拼豆 / 像素化工具技术拆解

**Status**: completed (Codex @ 2026-05-24) — 产出：[existing_tools.md](../../01_research/tech/existing_tools.md), [github_landscape.md](../../01_research/tech/github_landscape.md), [competitor_samples](../../01_research/tech/competitor_samples/)
**Owner**: Codex
**Priority**: 中
**Estimated**: 1-2 天

---

## 背景
PinDou 的差异化是"AI 预处理 + 智能量化 + 可手工编辑"三段式，但前提是要知道**对手在用什么技术**、**为什么人像效果差**、**有哪些可借鉴的点**。本任务给后续 PRD 和算法选型提供竞品基线。

## 目标
拆解三类现有工具的技术栈、算法、商业化模式，输出可借鉴 / 必须避开的清单。

## 调研对象

### 1. GitHub 仓库（按附录 A 关键词列表扫）
重点关键词：
- `perler bead pattern`, `hama bead generator`, `bead pattern maker`
- `pixelization`, `pixel art converter`, `image to pixel art`
- `WuhanLuxin/Pixelization`（ECCV 2022 官方实现，**必看**）
- `AUTOMATIC1111/stable-diffusion-webui` pixel art LoRA 生态
- `comfyanonymous/ComfyUI` 的 pixel art workflow

筛选门槛：
- Star > 500 优先
- 最近 12 个月有更新优先
- 有 demo / hosted service 能直接看效果优先
- 协议：MIT / Apache 2.0 优先，**GPL 标 "⚠️ 商业化风险"**

### 2. 微信小程序竞品（重点）
至少覆盖：
- 拼豆小师傅
- 一粒像素豆
- 拼豆图纸生成器 Pro
- 自行搜索 "拼豆图纸" 关键词找出 Top 5

能反编译或抓包看算法路径就抓（小程序前端通常是 JS，wxapkg 可解包）；不行就用黑盒测试推断（用同一张测试图传进去看输出）。

### 3. Web 端工具
至少覆盖：
- Beadr.app
- makebeadpatterns
- Pixelogic
- Perler 官方 pattern generator

---

## 每个工具的产出格式（每个一段）
```markdown
### [工具名]
- **类型**：GitHub 仓库 / 小程序 / Web
- **链接**：
- **Star / 用户量**：（GitHub: star 数 + 最近 commit；小程序：可见用户数 / 评分；Web：Alexa / SimilarWeb 估算）
- **技术栈**：（前端 / 后端 / 算法）
- **核心算法**：（K-means? Median-cut? 是否有 AI 预处理？是否有抖动？）
- **量化方式**：（RGB 最近邻 / CIELAB ΔE / 神经网络？色卡匹配怎么做？）
- **是否含 AI**：（有 / 无 / 部分。如果有，是什么模型？）
- **商业化模式**：（免费 / 订阅 / 按次 / 广告 / 高客单服务）
- **价格**：（如能查到）
- **优缺点**：（实测体验 + 用户评价）
- **我们可借鉴点**：
- **我们必须避开的坑**：
```

## 输出位置
- 主报告：`01_research/tech/existing_tools.md`
- GitHub landscape 单独成文：`01_research/tech/github_landscape.md`
- 小程序截图 / 测试输出存：`01_research/tech/competitor_samples/`

## 验收标准
- [ ] GitHub 仓库 ≥ 10 个（含 Pixelization、IPAdapter 等 SOTA 仓库）
- [ ] 小程序竞品 ≥ 5 个
- [ ] Web 工具 ≥ 3 个
- [ ] 每个工具至少有一张实测输入 / 输出图（共用同一组测试图：1 人像 + 1 宠物 + 1 卡通）
- [ ] 输出一节 "Top 5 我们必须吸取的教训"
- [ ] 输出一节 "Top 3 我们可以直接复用的开源代码 / 算法"
- [ ] `data_sources.md` 追加所有外部引用

## 不要做
- 不要做算法跑分（那是任务 B）
- 不要做 AI 预处理 PoC（那是任务 C）
- 不要爬取竞品用户数据用于市场营销（合规风险）
