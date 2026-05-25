# PinDou PRD v0.1

> **版本**：v0.1（草案，待用户 review）
> **日期**：2026-05-24
> **撰写**：Claude Code（基于 9 个 ADR + 9 个 Phase 0 调研任务产出）
> **分支**：`phase1`
> **状态**：待用户 review → 评审通过 → 冻结 v1.0 → 进入 Phase 2 实施
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

### 不服务的用户群
- 追求"像照片一样写实"的用户（ADR-005a 写实路线降级到 Phase 2+）
- 自己玩高难度大尺寸（>120×120）的核心玩家（Phase 5+ 考虑）

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
  [选择风格预设]
   Q版人像 / Q版宠物 / Q版情侣 / 通用卡通
        ↓
  [选择尺寸预设]
   60×80（小，~30 元材料）
   80×100（中，~80 元材料）
   100×120（大，~150 元材料）
        ↓
  [检查免费额度 / 付费状态]
   - 免费 3 次未用完 → 直接生成
   - 用完 → 提示「加客服扫码付 9.9 单次 / 28 月卡」或「看激励视频续 1 次」
                                              （流量主在 UV ≥ 1000 后开通）
        ↓
  [触发 PreviewProvider 生成]
   ↓ 等待 30-60 秒
   ↓ UX：进度条 + 趣味文案 + "去看示例作品" 转场
        ↓
  [FinishedPreview 展示]
   ↓ 可操作：
   ↓   - 重新生成（同风格，新种子，消耗一次额度）
   ↓   - 切换风格 / 尺寸（重新走 PreviewProvider，消耗额度）
   ↓   - "我喜欢这个" → 加入待制作（暂存，不消耗额度）
   ↓   - 直接下载 Preview 图（分享到小红书）
        ↓
  [触发 PatternBuilder 生成]
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
- **首屏黄金 5 秒**：3 张爆款成品图轮播 + "30 秒生成你的拼豆图纸" + 上传按钮
- **付费时机**：用户已经看到 FinishedPreview → 喜欢 → 想要 PatternSheet → 此时弹付费
- **失败兜底**：PreviewProvider 失败 → 自动 fallback 到"普通量化"（ADR-005 fallback chain），不让用户看到报错

---

## §4 功能清单

### §4.1 上传图（P0 必做）
- 支持微信小程序内拍照 / 相册选图
- 单次 1 张，< 10 MB
- 自动 EXIF 旋转修正
- 客户端预检：尺寸 / 格式（jpg / png / webp）/ 文件大小
- 后端预审核（Phase 3 接入图片审核 SDK）

### §4.2 风格预设（P0 必做）
四个预设，按 ADR-005a 修订版均走 Q 版 / chibi 化：
- **Q 版人像**（单人正脸 / 半身）
- **Q 版宠物**（猫 / 狗 / 其他可识别动物）
- **Q 版情侣**（两人合影）
- **通用卡通**（其他场景兜底）

每个预设对应的 prompt 来自 `01_research/tech/prompts.md` + Task C 拼豆约束（"不新增原图没有的身体部位"等）。

**待定**（Phase 2+）：
- 写实人像（"忠于原貌"模式）
- 多人合影（≥3 人）

### §4.3 尺寸预设（P0 必做）
三档（按 Task C 拼豆领域调研）：
- **60×80**（小，~30 元材料成本，宠物 / 单人头像）
- **80×100**（中，~80 元材料成本，单人半身 / 双宠物）
- **100×120**（大，~150 元材料成本，情侣 / 全身像）

**待定**（Phase 2+）：自定义任意尺寸 / 超大尺寸

### §4.4 FinishedPreview（P0 必做）
- 调用 `PreviewProvider.generate()`（接口规范 §5.1）
- 等待 30-60 秒
- 展示：1024×1024 Q 版图，带 alpha 透明背景
- 用户可操作：重新生成 / 切风格 / 切尺寸 / 加入待制作 / 下载 / 分享

### §4.5 PatternSheet（P0 必做）
- 调用 `PatternBuilder.build()`（接口规范 §5.2）
- 默认 MARD 5mm 色卡（ADR-002 修订版 + Task I 确认）
- 输出：
  - 网格 grid[][]（每格 1 个色号或 NoBead）
  - 色号数量表（每色多少颗 + 建议加 5-10% 备用）
  - 坐标表（基础版只显示，高级版可导 Excel）
  - 总颗数 + 估算成本（按 Task I bead_skus_cn 平均价）
  - PDF 导出（高级版 P1）
  - 分区图（大尺寸自动拆，高级版 P1）

### §4.6 付费 / 变现（P0 必做）

按 ADR-003（修订）+ ADR-006 个人主体限制：

| 档位 | 价格 | 包含 | 实现方式 |
|------|------|------|---------|
| 免费层 | 0 | 3 次基础生成 | 注册即送 |
| 单次购 | 9.9 | 1 次 Preview + 基础 PatternSheet | **加客服微信扫码付** |
| 月卡 | 28 | 不限 Preview + 5 次高级 PatternSheet（PDF + Excel + 分区） | 加客服微信扫码付 |
| 激励视频续次 | 0（看广告） | 1 次基础生成 | 流量主开通后（UV ≥ 1000） |
| 人工精修 | 99 起 | 人工兜底高难度 | 加客服微信，外部接单 |

**为什么不用官方微信支付**：ADR-006 个人主体不能开通商户号。"加客服扫码"的具体实现：
- 小程序内付费按钮 → 弹窗显示客服微信二维码（你 / 女朋友的号）+ 订单号
- 用户长按二维码加好友 → 私下转账 → 客服后台手动开通额度
- 优点：合规、零成本
- 缺点：转化率打折 30-50%（用户路径断裂）；客服人工成本

**待 Phase 4 评估升级到个体工商户 + 微信支付**（FUTURE_WORK 第 6 条）

### §4.7 用户作品集（P0 必做）
- 自动保存所有生成的 Preview + PatternSheet
- 按 ADR-009：原图 30 天后自动删除；PatternSheet 永久保存（用户作品）
- 用户可删除任意作品（删除接口必须实现）
- 作品集可分享给朋友（生成卡片链接，含 Preview + PinDou 引导）

### §4.8 分享功能（P0 必做）
- 微信内分享卡片：Preview 缩略图 + 标题 + PinDou 入口
- 保存到相册：Preview 图 + 水印
- 引导小红书发布（提供简易文案模板）

### §4.9 不做（Phase 1 不在范围）
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
        size_preset: SizePreset,         # 60x80 / 80x100 / 100x120
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

### §5.2 `PatternBuilder` 接口

```python
class PatternBuilder:
    """
    本地确定性算法。从 FinishedPreview 生成拼豆制作图纸。
    Phase 1 实现：K-means + CIEDE2000 + 无抖动（Task B 推荐）
                  + 拼豆后处理（去孤点 / 黑边保护 / 透明背景识别）
    """

    def build(
        self,
        preview: bytes,                  # FinishedPreview PNG with alpha
        size: SizePreset,                # 60x80 / 80x100 / 100x120
        brand: str = "MARD",             # 品牌（Phase 1 默认 MARD，可切但 UI 不暴露）
        bead_diameter_mm: float = 5.0,   # 豆径（Phase 1 默认 5mm）
    ) -> PatternSheet:
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
    payment_method: str                # "wechat_qr_via_cs"（加客服扫码付）
    customer_service_handler: str | None  # 哪个客服处理的（你 / 女朋友）
    artwork_id: str | None             # 关联的作品（如果是按次购买）
```

### §6.5 私人素材保存策略（ADR-009 落地）
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

---

**PRD v0.1 结。等你 review。**
