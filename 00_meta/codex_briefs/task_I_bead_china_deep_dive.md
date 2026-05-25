# Task I — 中文社区拼豆深度调研（色卡 / 供应链 / 用户认知 / 上场工具反查）

**Status**: completed (Codex @ 2026-05-24) — public-web pass completed; XHS App / physical-card follow-up required
**Owner**: Codex
**Priority**: 高（Phase 1 PRD 数据契约填实之前完成）
**Estimated**: 4-6 天
**依赖**: Task H 全品牌色卡基线（作为对照基准）
**被依赖**: Phase 1 PRD 的"色卡数据契约"章节、ADR-002 默认色卡选择复核

---

## 完成产出

- 总入口：`01_research/colormap_china/README.md`
- 小红书公开入口 / 手工补采队列：`01_research/colormap_china/xhs_color_mentions.csv`
- 小红书 App 人工补采模板：`01_research/colormap_china/xhs_manual_collection_template.csv`
- KOL / 内容偏好：`01_research/colormap_china/xhs_kol_preferences.md`
- 国内 SKU 表：`01_research/colormap_china/bead_skus_cn.csv`
- 国内品牌热度排序：`01_research/colormap_china/brand_popularity_cn.md`
- 中文社区认知：`01_research/colormap_china/community_insights.md`
- 竞品工具色卡反查：`01_research/colormap_china/competitor_palette_reverse.md`
- 实物 vs 屏幕色差风险：`01_research/colormap_china/physical_vs_screen_delta.md`
- 国内供应链状态：`01_research/colormap_china/cn_supply_status.md`
- 供应链覆盖层：`01_research/colormap_china/china_market_status_overrides.json`
- 中文别名映射建议：`01_research/colormap_china/chinese_color_aliases.json`
- 可复现生成脚本：`01_research/colormap_china/build_china_deep_dive_outputs.py`
- 数据源留痕：`00_meta/data_sources.md`
- Phase 1 PRD 影响建议：`00_meta/codex_briefs/_questions_for_user.md`

合规说明：未登录小红书 / 淘宝 / 1688；未保存 KOL 图片、实物色卡照片、竞品输出图、商家联系方式或用户个人信息。小红书 200 篇完整样本与实物色卡 ΔE 需要用户 App 内人工补采和实物拍摄后继续填充。

---

## 背景
Task H 完成了色卡数据库的骨架（16 个 brand × diameter JSON + 跨品牌对照），但数据源**严重偏国际工具站**：
- HEX 主要来自 Bitbead / Pixel Pattern / get-colors-from-beans（英文工具页）
- 没有中国国内拼豆市场的实际数据
- 没有实物色卡照片做屏幕 HEX 校准
- 没有用户认知 / 中文色名 / 国内 KOL 偏好

用户指示：知识库需要"花很多精力去确定"，**小红书一定要爬和搜索**，并且要**看已经上场的拼豆工具**实际用什么数据。

本任务的产出会回过头**重新校准 Task H 的判断**，并直接决定 Phase 1 PRD 中：
- 默认色卡是否仍为 MARD 5mm（可能要换 Artkal 2.6mm）
- 色卡数据 schema 是否需要扩展（中文色名 / 实物 HEX / 销量热度字段）
- PatternBuilder 输出的色号在国内用户认知中是否友好

## 目标
**用国内用户实际买得到 / 用得上 / 认识的语言**重做一遍拼豆知识库。

---

## 调研维度

### 维度 1：小红书拼豆内容深度调研（用户指示重点）

**目标**：找出国内拼豆圈用户实际在用什么色卡 / 什么色号 / 什么品牌。

**搜索关键词**（至少各搜 50 篇笔记）：
- "拼豆色卡"、"拼豆品牌对比"、"MARD 色卡"、"COCO 色卡"、"Artkal 色卡"、"拼豆新色"
- "拼豆人像"、"拼豆宠物"、"拼豆情侣"、"拼豆图纸"
- "Q版拼豆"、"chibi 拼豆"
- 拼豆 KOL Top 20 账号的色卡相关笔记（参考 Task E 已识别的账号矩阵）

**数据采集**：
- 每篇笔记记录：账号 / 时间 / 互动数 / 提到的品牌 / 提到的色号 / 实物图（如有） / 评论中用户的色号反馈
- 高互动笔记（>500 赞）打标"高影响力"
- 关注"避雷帖"、"翻车帖"——这些通常暴露实物 vs 屏幕的色差问题
- 关注"新色发布"、"限定色"、"绝版色"——这些影响供应链稳定性判断

**输出**：
- `01_research/colormap_china/xhs_color_mentions.csv`：每行一个色号提及，含品牌 / 色号 / 笔记 URL / 互动数 / 上下文（教程 / 评测 / 避雷 / 晒图）
- `01_research/colormap_china/xhs_kol_preferences.md`：Top 20 KOL 的色卡偏好摘要

**合规边界**：
- 小红书 ToS 不允许大规模爬虫 → **用搜索 + 公开浏览 + 手动记录**（每天采集量控制在 200 篇内）
- 如有条件用小红书开放搜索 API
- 不复制 KOL 笔记原文长段进 git（只摘要 + URL 链接）
- 不保存 KOL 实物照片到 git（ADR-009 hard rule）

### 维度 2：1688 / 淘宝 / 京东实际 SKU + 价格 + 销量

**目标**：找出国内市场实际能买到什么 + 价格分布 + 哪个品牌真受欢迎。

**采集对象**：
- 1688：搜"拼豆批发"，取 Top 30 店铺，记录主营品牌 / 豆径 / 单色装规格 / 批发价
- 淘宝：搜"拼豆"，取销量 Top 30，记录品牌 / 套装色数 / 零售价 / 月销量
- 京东：搜同关键词，取自营 + Top 20 店铺

**字段**（per SKU）：
```
brand, bead_diameter_mm, sku_name, color_count, pack_count_per_color,
price_cny, currency_normalized_to_cny, platform, shop_name, shop_credit,
monthly_sales, stock_indicator, url, captured_at
```

**输出**：
- `01_research/colormap_china/bead_skus_cn.csv`：实际 SKU 表
- `01_research/colormap_china/brand_popularity_cn.md`：基于销量推断的国内品牌热度排序

**合规边界**：
- 1688 / 淘宝爬虫同样有 ToS 限制，**优先用 API / 优先小样本人工**
- 不爬商家联系方式 / 不爬用户评论中的个人信息

### 维度 3：百度贴吧 / B 站 / 拼豆 QQ 群文件 社区认知

**目标**：补小红书覆盖不到的硬核用户社区数据。

**调研对象**：
- 百度"拼豆吧" / "perler 吧"高赞 / 精华帖
- B 站搜"拼豆教程"、"拼豆色卡"，取播放量 Top 30 视频，提取色卡相关字幕 / 评论
- 拼豆 QQ 群文件（公开资源站索引，**不强求加入私群**）

**输出**：
- `01_research/colormap_china/community_insights.md`：核心结论 + 数据点

### 维度 4：已上场拼豆工具的色卡使用反查（用户指示重点）

**目标**：看竞品工具用什么色卡数据 + 怎么处理国内色卡。

**反查方法**：
1. 取 Task A 已识别的 Top 5 小程序 + Top 3 Web 工具
2. 用**同一组测试图**（3 张：人像 + 宠物 + 卡通，与 Task B / C 复用）传入每个工具
3. 看输出图纸用什么品牌色号 + 多少色号 + 是否支持品牌切换
4. 记录每个工具默认 palette 的色号 / HEX（如可读取）
5. 注意工具是否声明色卡来源 / 是否有版权声明

**字段**（per 工具）：
```
tool_name, type (mp/web), default_brand, default_diameter,
supports_brand_switch, brand_list, color_count, palette_hex_extracted,
quality_notes, observed_at
```

**输出**：
- `01_research/colormap_china/competitor_palette_reverse.md`：竞品色卡反查报告
- 对比表：竞品色卡 vs Task H 数据库 vs 1688/淘宝实际 SKU 的重合度

**合规边界**：
- 用 PinDou 项目身份测试竞品工具（不冒充其他用户）
- 不反编译 / 不抓取竞品后端数据（只看公开前端输出）
- 不复制竞品色卡数据直接入 Task I 输出（参考结论入 git，原始数据本地保留 + 删除）

### 维度 5：实物 vs 屏幕色差观察

**目标**：知道国内 MARD / Artkal 等品牌**熨烫后**的实物颜色和 Task H 的 HEX 差多少。

**数据来源**：
- 小红书 / B 站博主的实物色卡照片（拍照对比 / 拼豆作品)
- 提取实物色卡上同一色号的视觉色彩，与 Task H HEX 对比
- 关注"熨烫前 vs 熨烫后"的色变（拼豆熨烫会显著改变饱和度）

**输出**：
- `01_research/colormap_china/physical_vs_screen_delta.md`：报告 + 估算的"屏幕预览到实物的色彩校准矩阵"（如可推导）
- **不保存博主原图**（ADR-009 + 版权风险，仅记录观察结论 + 引用 URL）

### 维度 6：国内供应链状态

**目标**：哪些色号当前在售 / 哪些常缺货 / 哪些已停产 / 哪些是新色。

**数据来源**：
- 维度 2 的 SKU 表 + 库存指标
- 维度 1 的小红书"避雷帖"、"绝版色"、"新色发布"笔记
- 维度 3 的社区讨论

**输出**：
- 在每个 `*_<size>mm.json` 的 `stock_status` 字段基础上，新增 `china_market_status` 字段（值：`active` / `low_stock` / `discontinued_cn` / `new_release` / `unknown`）
- 报告：`01_research/colormap_china/cn_supply_status.md`

### 维度 7：中文色名 vs 官方色名映射

**目标**：让产品 UI 能显示用户认识的中文色名（"奶白"vs "M01 Pure White"）。

**数据来源**：
- 维度 1 / 维度 3 的用户口语化色名提及
- 高频用法 → 映射到官方色号

**输出**：
- `01_research/colormap_china/chinese_color_aliases.json`：每个官方色号附带 1-N 个国内常用别名
- schema:
  ```json
  {
    "brand": "MARD",
    "code": "M01",
    "official_name": "纯白",
    "aliases_cn": ["奶白", "糖霜白", "雪白"],
    "alias_sources": ["xhs:URL1", "xhs:URL2"]
  }
  ```

---

## 输出位置（新建子目录）

所有产出存到新建的 `01_research/colormap_china/`，与 Task H 的 `01_research/colormap/` 并列。

具体文件清单：
- `01_research/colormap_china/README.md` — 总入口 + 数据源 + 局限性 + 给 Phase 1 PRD 的建议
- `01_research/colormap_china/xhs_color_mentions.csv`
- `01_research/colormap_china/xhs_kol_preferences.md`
- `01_research/colormap_china/bead_skus_cn.csv`
- `01_research/colormap_china/brand_popularity_cn.md`
- `01_research/colormap_china/community_insights.md`
- `01_research/colormap_china/competitor_palette_reverse.md`
- `01_research/colormap_china/physical_vs_screen_delta.md`
- `01_research/colormap_china/cn_supply_status.md`
- `01_research/colormap_china/chinese_color_aliases.json`

---

## 工具与方法

- 爬虫：`requests` + `BeautifulSoup` 用于静态页；`playwright` 用于小红书 / 1688 / 淘宝（注意单日采集量上限）
- 数据清洗：`pandas`
- 色彩分析（实物 vs 屏幕）：`opencv-python` + `colormath`
- 数据源留痕：`00_meta/data_sources.md`

---

## 验收标准

- [ ] 小红书 ≥ 200 篇相关笔记的色号提及数据
- [ ] 1688 / 淘宝 / 京东 ≥ 100 个 SKU 完整字段
- [ ] 至少 5 个上场拼豆工具反查（≥ 3 小程序 + ≥ 2 Web）
- [ ] 实物 vs 屏幕色差报告含 ≥ 30 个色号对照
- [ ] 国内供应链状态报告 ≥ 50 个色号标注
- [ ] 中文色名映射 ≥ 100 个官方色号有中文别名
- [ ] Phase 1 PRD 调整建议（默认色卡 / schema 扩展 / 用户色名 UI 三方面）
- [ ] `data_sources.md` 全部数据源留痕
- [ ] commit 中**无**未授权第三方图片 / KOL 私人信息 / 商家联系方式

## 不要做

- ❌ 不爬登录态 / 私群 / 私聊
- ❌ 不复制 KOL 笔记原文长段（摘要 + URL）
- ❌ 不保存博主实物色卡照片到 git（ADR-009）
- ❌ 不反编译竞品 / 不抓竞品后端
- ❌ 不大规模爬虫（每平台每天 ≤ 200 条记录）
- ❌ 不把商家联系方式 / 用户个人信息入 git

## 关联

- 修订 Task H 数据偏倚问题（不是替代，是校准）
- 影响 ADR-002 默认色卡选择（如果调研发现 Artkal 2.6mm 国内更受欢迎，默认要换）
- 影响 Phase 1 PRD 的"色卡数据契约"章节
- 与 ADR-009 私人素材规则强对齐
