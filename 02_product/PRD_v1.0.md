# PinDou PRD v1.0

> **版本**：v1.0（已冻结，Phase 2 实施合同）
> **日期**：2026-05-24 冻结
> **撰写**：Claude Code
> **批准**：用户 2026-05-24
> **分支**：`phase1` → 合并 main → Phase 2 在 `phase2` 分支实施
> **状态**：✅ 已冻结。任何字段改名 / 接口变更必须开 ADR 通知所有依赖方
>
> **版本历史**：
> - v0.1（2026-05-24 草案）— 9 章首版
> - v0.2（2026-05-24 修订）— 双路径 + CDK + ADR-003 修订
> - **v1.0（2026-05-24 冻结）— 用户批准 v0.2 后版本号升级**
>
> **给 review 者的提示**：你不用一字一句改，只需回答几类问题——
> 1. 用户路径（§3）哪步漏了 / 多了 / 顺序不对？
> 2. 功能清单（§4）哪个该做 / 不该做 / 优先级要调？
> 3. 定价（§4.6）数字要改吗？
> 4. UX（§7）文案 / 风格倾向？
> 5. 我没问到的、你想要的、PRD 里没写的——列出来。

---

## §1 产品定位

**一句话**：PinDou 是面向中文用户的拼豆图纸 AI 生成微信小程序，专攻人像 / 宠物 / 情侣场景。用户上传一张照片，30-60 秒内拿到"Q 版成品预览图"和"拼豆制作图纸"两个交付物，可分享、可付费下载、可下单购买实体。

**与市面工具的差异**：
- 市面工具：纯脚本量化 + RGB 最近邻，对真实人像普遍失真
- PinDou：AI 预处理（Q 版化）+ 智能量化（CIEDE2000）+ 拼豆领域后处理（去孤点 / 黑边保护 / 透明背景识别）
- 核心卖点：**人像 / 宠物 / 情侣的 Q 版拼豆，做出来既像本人又可爱**

**商业目标**：副业现金流，月入 6,000-10,000 RMB（详见 ADR-003）

---

## §2 用户画像

### 主要用户群（Phase 1 服务）
| 维度 | 描述 |
|------|------|
| 性别 | 女性 70% / 男性 30% |
| 年龄 | 18-35 岁为主 |
| 来源 | 小红书（ADR-004 冷启动唯一渠道）|
| 场景 | 情侣 / 闺蜜 / 宠物纪念 / 礼物 |
| 痛点 | 现有工具人像失真；自己拼豆没色卡素材；想做出"能发小红书"的成品 |
| 付费意愿 | 9.9-99 元区间高，月卡观望 |
| 设备 | 微信小程序为主（手机），高清原图上传需求中等 |

### 次要用户群（Phase 2+ 考虑）
- 拼豆教学 / 培训机构（B 端批量）
- 文创 / 礼品定制商家（B2B2C）
- PC 用户（Web 端补齐后服务）

---

## §3 用户路径（核心流程）

```
[小红书博主笔记 / 朋友分享]
        ↓
  [进入 PinDou 小程序]
        ↓
  ┌─ 首次：阅读用户协议 + 单独同意"上传人像"条款（ADR-009 + Task F 合规）
  │
  ↓
  [首页：上传照片入口 + 作品展示墙]
        ↓
  [上传 1 张照片] ─── 客户端检查：尺寸 / 格式 / 大小（< 10 MB）
        ↓                          内容审核（生成前）— Phase 3 接入
        ↓
  [选择生成方式 — 双路径分支]
   ┌─────────────────────────┬──────────────────────────────┐
   │  快速生成（脚本路径）    │  AI 精品生成（AI 路径）       │
   │  免费每日 3 次 + 广告续  │  首次体验 1 次免费 / 后付费   │
   │  质量：基础              │  质量：明显更好（Q 版化）      │
   └─────────────────────────┴──────────────────────────────┘
                ↓                              ↓
        [选择尺寸预设]              [选择风格预设 + 尺寸预设]
        60×80 / 80×100 / 100×120    Q版人像 / Q版宠物 / Q版情侣 / 通用卡通
                ↓                              ↓
        [检查免费 / 广告额度]        [检查 AI 额度]
        - 当日剩余 → 直接生成        - 首次体验 → 直接生成
        - 用完 → 看激励视频续次      - 已体验 → 付费 9.9 / 月卡 / CDK 兑换
                ↓                              ↓
        [跳过 PreviewProvider]      [触发 PreviewProvider 生成]
                ↓                    ↓ 等待 30-60 秒
                ↓                    ↓ UX：进度条 + 趣味文案 + 转场
                ↓                              ↓
                ↓                    [FinishedPreview 展示]
                ↓                    ↓ 可操作：重生成 / 切风格 / 加入待制作 / 下载分享
                ↓                              ↓
                └──────────┬───────────────────┘
                           ↓
  [触发 PatternBuilder 生成]
   ↓ 输入分两种：
   ↓   - 脚本路径：原图直接量化（K-means + CIEDE2000 + 无抖动）
   ↓   - AI 路径：FinishedPreview 量化（同算法 + 拼豆后处理）
   ↓ 即时（本地算法，< 1 秒）
   ↓ 默认 MARD 5mm；2.6mm 隐藏入口（Phase 1 不暴露 UI 但配置可切）
        ↓
  [PatternSheet 展示]
   ↓ 基础版（免费 / 基础包）：
   ↓   - 简单网格图
   ↓   - 总颗数 + 色号数量表
   ↓ 高级版（月卡 / 单独购）：
   ↓   - PDF 高清图纸
   ↓   - Excel 坐标表
   ↓   - 分区图（大尺寸自动拆 10×10 / 20×20）
   ↓   - 购物清单（淘宝 / 1688 链接 — 来自 Task I bead_skus_cn）
        ↓
  [用户作品集 / 分享 / 复购入口]
   ↓ 作品自动保存（按 ADR-009 隐私规则，30 天后自动删原图，保留 PatternSheet）
   ↓ 分享按钮：生成"卡片图"（Preview + 简易二维码 + PinDou logo）
   ↓ 复购入口：人工精修（99 起，跳客服微信）/ 实体拼豆套装购买（Phase 2+ 接入）
```

### 关键 UX 切片
- **首屏黄金 5 秒**：3 张爆款 AI 成品图轮播 + "30 秒生成你的拼豆图纸" + 上传按钮
- **双路径切换的 UX**：上传后展示"快速生成"vs"AI 精品"对比示例图（同一张原图的两个输出），让用户感受差异自然选 AI
- **付费时机**：用户已经体验 1 次 AI 看到效果 → 想再次生成 / 切风格 → 此时弹付费
- **CDK 入口**：付费弹窗里附"有 CDK？"按钮，引导到兑换页
- **失败兜底**：PreviewProvider 失败 → 自动 fallback 到脚本路径量化输出（ADR-005 fallback chain），用户看不到报错

---

## §4 功能清单

### §4.1 上传图（P0 必做）
- 支持微信小程序内拍照 / 相册选图
- 单次 1 张，< 10 MB
- 自动 EXIF 旋转修正
- 客户端预检：尺寸 / 格式（jpg / png / webp）/ 文件大小
- 后端预审核（Phase 3 接入图片审核 SDK）

### §4.2 生成方式选择（P0 必做，v0.2 新增）

上传后展示双路径卡片，让用户主动选择：

| 卡片 | 标题 | 副标题 | 示例图（用同一原图） |
|------|------|--------|---------------------|
| **快速生成** | "30 秒拿图纸" | "免费，每日 3 次" | 脚本量化样例图（块面感强、不 Q 版化） |
| **AI 精品生成** | "AI 帮你 Q 版化，更可爱" | "首次免费体验，之后 9.9 起" | AI 生成 Q 版样例图（明显更好看） |

**关键 UX**：双示例图必须用**同一张原图**生成，让差异一目了然。这是 ADR-003 修订决策的核心：差异化产生付费动机。

### §4.3 风格预设（AI 路径专属，P0 必做）
仅 AI 路径需要选风格；脚本路径直接按原图量化。

四个预设，按 ADR-005a 修订版均走 Q 版 / chibi 化：
- **Q 版人像**（单人正脸 / 半身）
- **Q 版宠物**（猫 / 狗 / 其他可识别动物）
- **Q 版情侣**（两人合影）
- **通用卡通**（其他场景兜底）

prompt 来自 `01_research/tech/prompts.md` + Task C 拼豆约束（"不新增原图没有的身体部位"等）。

**待定**（Phase 2+）：写实人像（"忠于原貌"模式）/ 多人合影（≥3 人）

### §4.4 尺寸预设（两路径共用，P0 必做）

尺寸预设必须对齐拼豆板物理网格，详见 `04_architecture/ADRs/ADR-010-pegboard-aligned-size-presets.md` 与 `01_research/colormap/pegboard_sizes.md`。

Phase 2 中国市场默认按用户实物反馈的 26 格国产拼豆板序列：
- **26×26 单板 Q 版**（默认，一块板，适合头像 / 单宠物 / 小白对牌）
- **52×52 双板**（2×2 板区，适合更完整主体）
- **78×78 三板**（3×3 板区，适合半身 / 双主体）
- **104×104 四板**（4×4 板区，适合大幅图纸）

#### §4.4.1 Phase 2 默认尺寸调优

Phase 2 v1 质量评审曾把默认尺寸从 `80×100` 调整为 `40×40`，解决过密和照片纹理问题。v2 继续发现 `40×40` 不是物理拼豆板尺寸，用户不能直接按板摆豆。

产品默认生成尺寸调整为 `26×26`，优先得到粗黑边、少色数、单板可制作的小图纸；`52×52`、`78×78`、`104×104` 保留为更大作品预设。

公开资料显示 Hama / Perler / Artkal 常见 5mm 大方板更接近 `29×29`。Phase 2 暂不暴露国际板型选择；未来若支持这些品牌，需要新增 `board_profile` 而不是复用当前国产 26 格默认。

#### §4.4.2 自定义尺寸规则（2026-05-26 v3 调优加入）

Phase 2 支持用户在四个推荐预设之外输入自定义 `宽×高`：
- 格式：整数 `WIDTHxHEIGHT`，例如 `30x30` / `45x45`
- 范围：最小 `20×20`，最大 `200×200`
- 长宽比：`0.5-2.0`
- 预设 `26×26` / `52×52` / `78×78` / `104×104` 保持推荐位
- 若宽高不是 26 的整数倍，后端仍允许生成，但 `metadata.warning` 返回“不对齐 26 格拼豆板，建议准备约 N 块板后裁边”；前端用黄色提示展示

### §4.5 脚本快速生成路径（P0 必做，v0.2 新增）

**用户视角**：上传图 → 选尺寸 → 5-10 秒拿到 PatternSheet。

**技术**：
- 直接调 `PatternBuilder.build(raw_image=...)`（接口规范 §5.2 扩展）
- 不调用 `PreviewProvider`，没有 AI 风格化
- 算法：K-means + CIEDE2000 + 无抖动（Task B 推荐）+ 拼豆后处理（去孤点 / 黑边保护 / 透明背景识别）
- 默认 MARD 5mm 色卡

**额度规则**（ADR-003 修订）：
- 每日 3 次免费
- 用完后看激励视频续 1 次（每日上限 10 次）
- 激励视频依赖流量主开通（UV ≥ 1000 + 工具类目）

**质量特征**：基础可用，但对人像 / 宠物效果一般（这是设计意图——让用户感受到 AI 路径的差异）。

**默认行为：整张铺豆**（无背景识别，材料贵），但提供"试试自动去白底"功能：

#### §4.5.1 试试自动去白底（2026-05-25 review 加入）
- 用户在 PatternSheet 结果页可点 `[试试自动去白底]` 按钮
- 触发 `PatternBuilder.build(raw_image=..., auto_remove_white_bg=True)`
- 算法：检测四角颜色 → 若与纯白 ΔE < 8 则 flood fill 标记为 NoBead；否则 toast "未检测到白底" 不消耗配额
- 配额规则（详见 ADR-003 修订）：
  - 每日免费 1 次
  - 用完看激励视频续 1 次（每日上限 5 次）
  - **AI 路径无此按钮**——AI 自动识别背景是付费版差异化护城河
- 前端 UX（Gemini Phase 2 后期补）：
  - 按钮位于 `result-basic.vue` 主 CTA 区上方
  - 点击后 toast："正在分析背景…" + spinner
  - 成功 → PatternSheet 区域柔和淡入新结果 + toast "已去白底，预计省 N 颗豆"
  - 失败（未检测到）→ toast 红色提示，**不消耗配额**

### §4.6 AI 精品生成路径 — FinishedPreview（P0 必做）

**用户视角**：上传图 → 选风格 + 尺寸 → 等待 30-60 秒 → 看 Preview → 决定要不要 PatternSheet。

**技术**：
- 调用 `PreviewProvider.generate()`（接口规范 §5.1）
- 等待 30-60 秒
- 展示：1024×1024 Q 版图，带 alpha 透明背景
- 后续调 `PatternBuilder.build(preview=...)` 生成 PatternSheet

**额度规则**：
- 首次进入"AI 精品"免费体验 1 次（生命周期 1 次，不每日重置）
- 已体验后：付费 9.9 / 月卡 28 / CDK 兑换 / 人工精修

**用户可操作**（仅 AI 路径）：
- 重新生成（同风格新种子，消耗 1 次 AI 额度）
- 切换风格 / 尺寸（重新走 PreviewProvider，消耗额度）
- "我喜欢这个" → 加入待制作（暂存，不消耗额度）
- 直接下载 Preview 图（分享到小红书）

#### §4.6.1 生成前确认（2026-05-26 v7 调优加入）

普通用户在选择"快速生成"或"AI 精品生成"后，前端先弹出确认 sheet，不直接发起生成请求。确认内容包括生成方式、尺寸、预计颗数、预计色号、预计时长与消耗说明：

- 快速生成：展示今日免费剩余次数；若已用完，提示需看 1 次广告续次。
- AI 精品：展示首次体验 / 可用 AI 额度 / 9.9 单次购、月卡、CDK 兑换选项。
- 月卡用户、测试不限量用户可通过 `SKIP_CONFIRM_FOR_PREMIUM=true` 跳过确认页，保持连续生成体验。
- AI 路径确认页提供"我有 CDK 兑换码"入口，跳转 `pages/cdk/redeem`。

### §4.7 PatternSheet 展示与导出（两路径共用，P0 必做）

`PatternBuilder` 输出后展示：
- 网格 grid[][]（每格 1 个色号或 NoBead）
- 色号数量表（每色多少颗 + 建议加 5-10% 备用）
- 总颗数 + 估算成本（按 Task I bead_skus_cn 平均价）

**基础版**（脚本路径默认 + AI 单次购）：
- 简单网格 PNG
- 色号数量表

**高级版**（月卡 / CDK 月卡）：
- PDF 高清图纸
- Excel 坐标表
- 分区图（固定 2×2 四区）
- 购物清单（含 Task I bead_skus_cn 的真实链接）

#### §4.7.1 分区查看实现细节（2026-05-26 v4 调优加入）

手机屏幕内联展示完整 `26×26 / 52×52 / 78×78 / 104×104` 图纸时，色号会受物理宽度限制变小。Phase 2 采用两层查看：

- 结果页主图只做缩略预览 + 关键信息；点击主图调用微信原生 `previewImage`，支持双指缩放、平移和保存。
- 后端保存完整带网格 / 色号的 PNG 到 `/static/patterns/`，通过 `PatternSheet.metadata.labeled_image_url` 暴露给前端。
- 高级分区图接口：`GET /api/v1/pattern/{artwork_id}/partitions`。
- 固定 2×2 四区：数组顺序为左上 / 右上 / 左下 / 右下；每张子图包含行列范围、全图位置缩略图和清晰色号。
- 前端 `pages/result/partitions` 以 2×2 网格展示四张分区图；点击任一子图调用 `previewImage` 全屏查看。
- 功能属于高级 PatternSheet 能力；Phase 2 入口免费可见，付费拦截可在月卡逻辑稳定后补上。

#### §4.7.2 高级导出实现窗口（2026-05-26 v8 补充）

Phase 2 当前交付 PNG 主图 + 2×2 分区预览，先解决手机查看和拼接指导。PDF 高清图纸、Excel 坐标表、打印版分区图、邮件发送与购物清单导出统一延后到 backend task 7.5，不在 v8 内实现。

### §4.8 付费 / 变现（P0 必做，v0.2 大改）

按 ADR-003 修订版：

| 档位 | 价格 | 包含 | 实现方式 |
|------|------|------|---------|
| 脚本免费 | 0 | 每日 3 次脚本生成 | 注册即享 |
| 激励视频续次 | 0（看广告） | 1 次脚本生成 | 流量主开通后（UV ≥ 1000） |
| AI 体验 | 0 | 1 次 AI 生成（生命周期 1 次） | 注册即享 |
| AI 单次购 | 9.9 | 1 次 AI 生成 + 基础 PatternSheet | **加客服微信扫码付** |
| 月卡 | 28 | 不限 AI 生成 + 高级 PatternSheet（PDF + Excel + 分区） | 加客服微信扫码付 |
| **CDK 兑换** | 由 CDK 类型决定 | 按 CDK 类型解锁额度 / 月卡 | 见 §4.9 |
| 人工精修 | 99 起 | 人工兜底高难度 | 加客服微信，外部接单 |

**为什么不用官方微信支付**：ADR-006 个人主体不能开通商户号。"加客服扫码"具体实现：
- 小程序内付费按钮 → 弹窗显示客服微信二维码（你 / 女朋友的号）+ 订单号
- 用户长按二维码加好友 → 私下转账 → 客服后台手动开通额度
- 优点：合规、零成本
- 缺点：转化率打折 30-50%；客服人工成本

**待 Phase 4 评估升级到个体工商户 + 微信支付**（FUTURE_WORK 第 6 条）

### §4.9 CDK 兑换（P0 必做，v0.2 新增）

**业务目的**：在小红书 / 闲鱼销售 CDK 字符串作为引流和裂变工具，绕过小程序内付费的客服扫码摩擦。

**CDK 类型**（ADR-003 修订）：
- `single_use`：兑换 1 次 AI 生成
- `monthly_card`：兑换 1 个月月卡
- `credit_pack_5` / `credit_pack_10`：兑换 N 次 AI 生成

**用户路径**：
- 用户在闲鱼 / 小红书购买 CDK（你 / 女朋友卖 CDK，价格略低于官方）
- 用户在小程序"我的 - 兑换 CDK"输入 18 位字符串
- 系统验证 → 标记 CDK 已使用 → 加额度 / 开通月卡

**后台**：
- 你 / 女朋友通过管理后台**批量生成 CDK** + 导出列表用于销售
- 监控异常兑换（同 IP 短时间大量兑换 → 标记可疑）

**防滥用**：
- 每个 CDK 一次性使用
- 兑换后绑定首次兑换用户
- 18 位字符串使用安全字典（避免歧义字符 I/O/0/1）

**UI 入口**：
- 我的页面有"兑换 CDK"按钮
- 付费弹窗里附"有 CDK？"小字按钮
- AI 体验用完的弹窗附"输入 CDK 解锁"选项

### §4.10 用户作品集（P0 必做）
- 自动保存所有生成的 Preview + PatternSheet
- 按 ADR-009：原图 30 天后自动删除；PatternSheet 永久保存（用户作品资产）
- 用户可删除任意作品（删除接口必须实现）
- 作品集可分享给朋友（生成卡片链接，含 Preview + PinDou 引导）

### §4.11 分享功能（P0 必做）
- 微信内分享卡片：Preview 缩略图 + 标题 + PinDou 入口
- 保存到相册：Preview 图 + 水印
- 引导小红书发布（提供简易文案模板）

### §4.12 不做（Phase 1 不在范围）
- 多人协作 / 实时协作
- 自有色卡 / 自定义色卡导入
- 3D 立体拼豆
- 社区（评论 / 关注 / 点赞）
- Web 端 UI 完整版（只做骨架）
- 写实人像风格
- 复杂图层 / 抠图编辑器
- 实体拼豆销售（Phase 2+ 接入第三方）

---

## §5 接口契约（Phase 2 实施合同）

### §5.1 `PreviewProvider` 接口

```python
class PreviewProvider:
    """
    AI 风格化生成器。外部 API 调用，不稳定，需 fallback chain。
    Phase 1 实现：P1 反代 gpt-image-2
    Phase 2+ 扩展：火山即梦 / 阿里通义万相（如 ADR-007 触发条件命中）
    """

    def generate(
        self,
        image: bytes,                    # 用户原图（原始字节）
        style_preset: StylePreset,       # Q版人像 / Q版宠物 / Q版情侣 / 通用卡通
        size_preset: SizePreset,         # 26x26 / 52x52 / 78x78 / 104x104 / custom WIDTHxHEIGHT
        seed: int | None = None,         # 可选随机种子，重生成时用
    ) -> PreviewResult:
        ...


@dataclass
class PreviewResult:
    image: bytes                          # PNG with alpha (transparent bg)
    image_format: str = "png"
    target_resolution: tuple = (1024, 1024)
    target_color_count: int                # 12-24, 实际生成的色数
    provider_used: str                     # "xiaochi_gpt_image_2" etc.
    fallback_count: int = 0                # 触发了几次 fallback
    cost_estimate: float                   # 单次成本（占位，反代当前 0）
    latency_ms: int                        # 实际耗时
    metadata: dict                         # provider-specific 扩展字段


# Fallback chain（必须实现）：
# 主 PreviewProvider → 备 PreviewProvider → "普通量化兜底"
# 兜底逻辑：调 PatternBuilder 直接量化原图，输出当 Preview（视觉差，但不报错）
```

#### §5.1.1 Internal `PreviewResult` vs HTTP API 返回（Phase 2 task 2 review 落档）
上面的 `PreviewResult` 是**后端内部 dataclass**（provider 接口传递），`image: bytes` 留给 provider 内部。
**HTTP API 返回前端的不是 bytes**，而是 `to_frontend_dict()` 转换后的精简字段：

```typescript
// 前端消费的字段（与 05_frontend/api/index.ts 对齐）
interface PreviewResultDTO {
  preview_id: string          // 后端保存 PNG 到 PINDOU_PREVIEW_DIR 后生成的 ID
  image_url: string           // 静态访问 URL（/static/previews/<id>.png）
  image_format: string
  target_resolution: [w, h]
  target_color_count: int
  provider_used: string
  fallback_count: int
  cost_estimate: float
  latency_ms: int
  metadata: dict              // 含 fallback_chain_failures 等监控信息
}
```

**桥接约定**：
- Provider 内部：保留 `image: bytes`（chain 计算 / fallback 转 PatternBuilder 用）
- API 端点（task 5 实现）：调 `result.to_frontend_dict()` + 落盘 PNG + 返回 URL
- 前端通过 `image_url` 异步加载图片，不阻塞 JSON 响应

### §5.2 `PatternBuilder` 接口

```python
class PatternBuilder:
    """
    本地确定性算法。从原图或 FinishedPreview 生成拼豆制作图纸。
    Phase 1 实现：K-means + CIEDE2000 + 无抖动（Task B 推荐）
                  + 拼豆后处理（去孤点 / 黑边保护 / 透明背景识别）

    支持两种输入（PRD v0.2 双路径修订）：
    - 脚本路径：raw_image 直接量化（无 AI 风格化）
    - AI 路径：preview 量化（已经 Q 版化）
    """

    def build(
        self,
        size: SizePreset,                # 26x26 / 52x52 / 78x78 / 104x104 / custom WIDTHxHEIGHT
        # 两种输入二选一：
        preview: bytes | None = None,    # AI 路径：FinishedPreview PNG with alpha
        raw_image: bytes | None = None,  # 脚本路径：用户原图（jpg/png）
        # 可选参数：
        brand: str = "MARD",             # 品牌（Phase 1 默认 MARD，可切但 UI 不暴露）
        bead_diameter_mm: float = 5.0,   # 豆径（Phase 1 默认 5mm）
        mode: str = "auto",              # auto / script / ai；auto 根据输入判断
    ) -> PatternSheet:
        """
        脚本路径处理：原图 → 主体裁切 → 缩放到目标尺寸 → 量化 → 拼豆后处理
        AI 路径处理：preview 已经主体居中 → 缩放 → 量化 → 拼豆后处理
        """
        ...


@dataclass
class PatternSheet:
    grid: list[list[ColorRef | NoBead]]   # 二维网格，shape = (size.h, size.w)
    color_counts: dict[str, int]          # { "M01": 234, "M12": 89, ... }
    bead_total: int                        # 总颗数（不含 NoBead）
    coords: list[tuple[int, int, str]]    # [(row, col, color_code), ...]
    no_bead_mask: list[list[bool]]        # 哪些格是 NoBead
    palette_used: list[ColorRef]           # 实际用到的色号子集
    estimated_cost_cny: float             # 总成本（基于 Task I bead_skus_cn 平均价）
    suggested_buffer_pct: int = 10        # 建议加 5-10% 备用
    brand: str                             # MARD
    bead_diameter_mm: float                # 5.0


@dataclass
class ColorRef:
    brand: str                  # MARD
    code: str                   # M01
    name_cn: str                # 纯白
    name_en: str | None         # Pure White
    hex: str                    # #FFFFFF
    rgb: tuple[int, int, int]
    bead_diameter_mm: float
```

### §5.3 输出导出接口（Phase 1 P1）

```python
class PatternExporter:
    def to_simple_grid_png(self, pattern: PatternSheet) -> bytes: ...    # 基础包
    def to_pdf(self, pattern: PatternSheet) -> bytes: ...                # 高级包
    def to_excel(self, pattern: PatternSheet) -> bytes: ...              # 高级包
    def to_partition_images(self, pattern: PatternSheet, block_size: int = 20) -> list[bytes]: ...  # 高级包
    def to_shopping_list(self, pattern: PatternSheet) -> ShoppingList: ...  # 高级包，含 Task I 真实链接
```

### §5.4 接口冻结规则
- v1.0 PRD 评审通过后，上述接口 schema 冻结
- 任何字段改名 / 删除必须开 ADR 并通知所有依赖方
- 字段新增允许（向后兼容）

---

## §6 数据模型

### §6.1 色卡 / 豆系（来自 Task D / H / I）

**数据存储策略**（Phase 2 task 4 review 落档）：
- **bead_skus / 色卡 palette 保持文件型**，不进 SQL：
  - 数据相对静态（月度更新频率），写入由 Codex 数据更新任务批量执行
  - 业务运行时只读，`colormap/loader.py` 缓存内存（启动时一次加载）
  - 进 SQL 反而增加 migration / 数据同步负担
- **迁 SQL 的触发条件**（Phase 4+）：① 需要"实时库存 / 实时价格"展示 ② 多品牌 SKU 总数 > 5000 行导致内存压力 ③ 后台需要动态增删 SKU 不重启服务

延用 `01_research/colormap/<brand>_<size>mm.json` schema，**新增字段**（Task I 建议）：

```json
{
  "brand": "MARD",
  "bead_diameter_mm": 5.0,
  "code": "M01",
  "name_cn": "纯白",
  "name_en": "Pure White",
  "hex": "#FFFFFF",
  "rgb": [255, 255, 255],
  "lab": [100.0, 0.0, 0.0],
  "category": "白色系",

  "// 已有": "...",
  "stock_status": "common",

  "// Task I 新增字段": "",
  "china_market_status": "active",
  "aliases_cn": ["奶白", "糖霜白"],
  "source_confidence": {
    "hex": "medium",
    "price": "low",
    "stock": "high"
  }
}
```

**SKU 表**（独立文件，来自 Task I bead_skus_cn.csv）：
```
bead_skus.json:
[
  {
    "brand": "MARD",
    "bead_diameter_mm": 5.0,
    "code": "M01",
    "platform": "taobao",
    "shop_name": "...",
    "shop_credit": 5,
    "currency": "CNY",
    "pack_count": 1000,
    "price": 6.5,
    "monthly_sales": 234,
    "url": "...",
    "captured_at": "2026-05-24"
  }
]
```

### §6.2 用户

```python
@dataclass
class User:
    user_id: str                       # 微信 openid
    nickname: str
    avatar: str
    created_at: datetime
    free_credits_remaining: int = 3    # 注册即送
    paid_credits: int = 0              # 付费充值
    monthly_card_expires_at: datetime | None = None
    privacy_consent_at: datetime       # 隐私政策同意时间（合规留痕）
    sensitive_consent_at: datetime     # 单独同意"上传人像"
```

### §6.3 作品

```python
@dataclass
class Artwork:
    artwork_id: str
    user_id: str
    created_at: datetime
    original_image_url: str | None     # 原图 URL，30 天后删除（ADR-009）
    original_image_deleted_at: datetime | None
    style_preset: StylePreset
    size_preset: SizePreset
    preview_url: str                   # FinishedPreview URL（永久）
    thumbnail_url: str | None          # 作品集 200×200 缩略图 URL；可由后端从图纸 PNG 懒生成
    pattern_data: PatternSheet         # 完整图纸数据（永久）
    title: str | None
    is_paid_unlocked: bool = False     # 用户是否已付费解锁高级图纸
```

### §6.4 订单

```python
@dataclass
class Order:
    order_id: str
    user_id: str
    created_at: datetime
    sku: OrderSKU                      # 9.9 单次 / 28 月卡 / 99 人工精修
    amount_cny: float
    status: str                        # pending / paid_confirmed / refunded / failed
    payment_method: str                # "wechat_qr_via_cs" / "cdk_redemption"
    customer_service_handler: str | None  # 哪个客服处理的（你 / 女朋友）
    artwork_id: str | None             # 关联的作品（如果是按次购买）
    cdk_code: str | None               # 如果通过 CDK 兑换
```

### §6.5 CDK（兑换码，PRD v0.2 新增）

```python
@dataclass
class CDK:
    cdk_code: str                     # 18 位安全字典字符串（无 I/O/0/1 歧义）
    cdk_type: CDKType                 # single_use / monthly_card / credit_pack_5 / credit_pack_10
    value: int                        # 兑换额度数值（single_use=1, credit_pack_5=5 ...）
    status: str                       # active / redeemed / expired / void
    batch_id: str                     # 批次号（管理后台批量生成时分配）
    created_at: datetime
    created_by: str                   # 谁生成的（你 / 女朋友 / 系统自动）
    expires_at: datetime | None       # 可选过期时间
    redeemed_by_user_id: str | None
    redeemed_at: datetime | None
    redemption_ip: str | None         # 兑换 IP（防滥用监控）
    sale_channel: str | None          # "xianyu" / "xhs_kol_giveaway" / "manual" 等
    notes: str                        # 备注（哪个博主合作 / 哪个团购等）


# 批量生成接口（管理后台）
def generate_cdk_batch(
    cdk_type: CDKType,
    count: int,
    expires_at: datetime | None = None,
    sale_channel: str | None = None,
) -> list[CDK]: ...
```

**安全设计**：
- 18 位字符串采用安全字典（避免 I/O/0/1）→ 实际使用 32 个字符
- 一次性使用（兑换后立刻 status=redeemed）
- 同 IP 短时间内（10 分钟）兑换 ≥ 5 个 CDK → 标记可疑 + 后台告警
- 兑换接口频率限制（同用户 1 分钟 ≤ 3 次尝试）

### §6.6 私人素材保存策略（ADR-009 落地）
- 原图：上传后存对象临时位置；用户作品确认保存 → 后端定时任务 30 天后删除
- AI 生成中间产物：生成完即删
- PatternSheet：永久保存（用户作品资产，不含原始图像信息）

---

## §7 UX 规范

### §7.1 等待 UX（最关键）
Preview 生成 30-60 秒是用户最容易流失的环节。设计：
- 进度条：分三段（"AI 正在画你的拼豆..." → "正在挑选最美色号..." → "马上就好啦~"）
- 趣味文案随机 1 句（10 句池子，避免重复）
- "去看示例作品"按钮 → 跳作品集墙，给用户找事做
- 30 秒后弹"还有 30 秒哦，你的作品 99% 完成"
- 60 秒未返回 → 提示"网络有点慢，要不要再试一次？"

### §7.2 错误提示
- 永远不显示英文报错
- 永远不显示技术细节（"Provider X timeout" → "网络有点慢，再试一次吧~"）
- 三类失败必有兜底文案：
  1. 上传失败：检查格式 / 大小，给具体建议
  2. Preview 生成失败：自动 fallback（用户看不到失败）
  3. 付费失败：明确说"加客服核对一下哦"

### §7.3 引导
- 首次进入：3 张爆款 Preview 轮播 + 一键"试一下" CTA
- 上传后：风格选择卡片带"猜你喜欢"标签
- Preview 出来后：自动滚到"加入待制作"按钮
- 付费弹窗：明确说"加客服微信扫码付"，二维码 + 订单号

### §7.4 中文色名（Task I 建议）
- 色号搜索 / 展示支持中文别名（"奶白""腮红粉"等）
- 但材料清单 / 购物清单仍显示官方 code（"M01 纯白"）
- 用户搜"奶白" → 匹配到 M01 → 显示"M01 纯白（别名：奶白）"

### §7.5 视觉风格（待 Gemini 设计稿落地）
- 整体：清新 / 可爱 / 偏小红书少女风
- 主色：粉色 / 米色系，避免冷感
- 字体：圆润感（避免硬棱角）
- 关键 CTA：高饱和粉 / 渐变橙

---

## §8 用户协议 + 隐私政策草案

### §8.1 用户协议要点（Task F 合规）
- 服务范围：图片处理 / 图纸生成工具
- 内容限制：禁止上传违法 / 违规 / 涉政 / 涉黄 / 涉未成年 / 第三方版权材料
- AI 生成标识：所有 Preview 标注"AI 辅助生成"（Phase 3 提审前必须落地）
- 退款规则：付费虚拟商品原则上不退；客服可酌情处理
- 责任限制：图纸仅供制作参考，不保证 100% 还原

### §8.2 隐私政策要点（Task F 合规 + ADR-009）

**收集**：
- 微信授权获取的：openid、nickname、avatar
- 用户上传的：照片（用于生成）
- 自动收集的：访问日志、错误日志（不含个人信息）

**使用**：
- 照片**仅用于**生成你的拼豆图纸
- 不会用于：广告 / 第三方分享 / 模型训练

**保存**：
- 原图：30 天后**自动删除**
- 生成的图纸：永久保存在你的作品集，可随时删除
- 错误日志：90 天后自动清理

**用户权利**：
- 查看 / 删除作品（小程序内）
- 撤回同意（删除账号入口）
- 投诉举报（联系客服邮箱）

**敏感个人信息**单独同意：
- 上传含人像照片前，弹出独立窗口告知 + 单独同意

**第三方共享**：
- 你上传的照片会经第三方 AI 服务（OpenAI 反代）处理用于生成图纸
  - **风险已告知**（ADR-007 用户接受，Phase 3 提审前评估披露程度）

### §8.3 待 Phase 3 完善
- 算法服务说明（如类目要求）
- 内容审核机制说明
- 跨境数据传输条款（如未迁国内服务器，必须详细披露）

---

## §9 非功能性需求

### §9.1 性能
- Preview 生成：P50 ≤ 45s / P95 ≤ 75s（按 Task C 实测 + buffer）
- PatternBuilder：P95 ≤ 3s（本地算法，100×120 网格）
- 小程序冷启动：≤ 2s
- 上传 5 MB 图片：在 4G 网络下 ≤ 10s

### §9.2 可用性
- PreviewProvider 可用率：≥ 95%（含 fallback chain）
- 后端服务可用率：≥ 99%（上海 8C16G 单机不要求高可用）
- 反代故障 > 6 小时 → 触发 ADR-007 监控 → 评估接通国产 fallback

### §9.3 监控（Phase 3 落地）
- API 调用成功率 / 延迟 P50/P95（Provider 维度）
- 用户漏斗：进入 → 上传 → Preview → PatternSheet → 付费
- 错误率 / 错误类型分布
- 反代服务健康检查（5 分钟一次）

### §9.4 安全
- 所有 API key 走 `.env`（不入 git）
- 用户图片 URL 加签名（防盗链）
- 客户端不存敏感 token
- ADR-009 私人素材规则落地（后端实现 + 定时删除任务）

### §9.5 合规（Phase 3 提审前）
- 类目：申请"工具 > 图像处理"，**不**申请 AIGC 类目（Task F 建议）
- 用户协议 / 隐私政策上线
- 单独同意机制实现
- 删除接口实现
- 上传内容审核 SDK 接入（Phase 3）
- 服务器选址：上海 8C16G 已就位，备案 Phase 2 末启动

---

## §A 附录

### §A.1 已用决策 ADR 映射
| 章节 | 依据 ADR |
|------|---------|
| §1 产品定位 | Charter |
| §3 用户路径 | ADR-008 双交付物 |
| §4.2 风格预设 | ADR-005 / ADR-005a |
| §4.3 尺寸预设 | Task C 拼豆领域知识 |
| §4.5 PatternBuilder | ADR-008 + Task B 算法基线 |
| §4.6 付费 | ADR-003 + ADR-006 个人主体限制 |
| §5 接口契约 | ADR-008 |
| §6 数据模型 | Task D / H / I |
| §7.4 中文色名 | Task I |
| §8 协议 | Task F + ADR-009 |
| §9.5 合规 | Task F + ADR-006 + ADR-007 |

### §A.2 待 v1.0 前补的内容（不阻塞 v0.1 review）
- 错误码字典（Phase 2 后端实现时定）
- 监控指标具体定义（Phase 3 接入埋点时定）
- 客服 SOP（你 / 女朋友需要定）
- 小红书发布文案模板（运营资产，女朋友 OCADU 视觉背景定）
- 算法备案 / 跨境合规具体方案（FUTURE_WORK 第 2/4 条触发后定）

### §A.3 待 Codex Phase 2 启动前补的数据
- "漫漫 / ManMan"品牌色卡（Task I 建议补，Task H 缺）
- 实物 vs 屏幕色差校准矩阵（用户线下采集 30 个色号实物对照）
- 小红书 ≥ 200 篇人工补采数据（用户暂不做，PRD v1.0 评审时再决定）
- **服务器硬盘大小**（用户上海 8C16G 20M 已就位，硬盘容量待用户查；影响 §6.6 用户作品存储策略 / 是否需要尽早接对象存储）

---

**PRD v0.1 结。等你 review。**
