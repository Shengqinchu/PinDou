# 拼豆知识库索引（Phase 2 review 加入）

> **用途**：让 Claude / Codex / Gemini 在任意上下文中快速定位拼豆数据。
> **撰写**：Claude Code 2026-05-25
> **更新策略**：色卡 / SKU / KOL 数据有大改动时同步更新这份索引（数量级变化、新 brand、schema 扩展）

---

## 1. 一句话定位

| 我想查什么 | 看哪个文件 |
|-----------|-----------|
| 某品牌色卡完整色号（HEX / LAB / 名称 / 价格） | `<brand>_<diameter>mm.json` |
| 跨品牌色号相似度（同豆径，CIEDE2000 近邻 Top 3） | `crossref_full.csv` |
| 国内市场实际 SKU + 价格 + 销量 | `colormap_china/bead_skus_cn.csv` |
| 国内用户口语化色名 → 官方色号 | `colormap_china/chinese_color_aliases.json` |
| 某色号在国内当前是否在售 / 停产 / 新色 | `colormap_china/china_market_status_overrides.json` |
| 小红书 KOL 用哪些色卡 / 哪些避雷 | `colormap_china/xhs_kol_preferences.md` |
| 已上场拼豆工具用什么色卡数据 | `colormap_china/competitor_palette_reverse.md` |
| 实物 vs 屏幕色差报告 | `colormap_china/physical_vs_screen_delta.md` |
| 后端代码怎么调用色卡 | `06_backend/pindou/colormap/loader.py` + `matcher.py` |

---

## 2. 色卡矩阵覆盖（Task D + Task H 完成）

| Brand | 2.5mm | 2.6mm | 5mm | 10mm | 数据源主线 |
|-------|-------|-------|-----|------|-----------|
| **MARD**（国产，Phase 1 默认）| — | ✅ `mard_2_6mm.json` | ✅ `mard_5mm.json`（291 色，主推）| ✅ `mard_10mm.json` | 公开工具页 + 1688 |
| **COCO**（国产）| — | ✅ `coco_2_6mm.json` | ✅ `coco_5mm.json`（80 色）| ✅ `coco_10mm.json` | 公开工具页 |
| **Hama**（丹麦，国际）| ✅ `hama_2_5mm.json` | — | ✅ `hama_5mm.json`（89 色）| ✅ `hama_10mm.json` | Hama 官方 + Bitbead |
| **Perler**（美国）| — | — | ✅ `perler_5mm.json`（117 色）| — | Perler 官方 |
| **Artkal**（国产）| — | ✅ `artkal_2_6mm.json`（221 色）| ✅ `artkal_5mm.json`（201 色）| ✅ `artkal_10mm.json` | Artkal 官方 + Pixel Pattern |
| **黄豆豆 / 咪小窝 / 盼盼** | — | — | ✅ `other_*_5mm.json` | — | 1688 / 淘宝 Top 30 |

**缺失项**：
- MARD / COCO / Artkal 的 10mm 没有可靠结构化公开色卡（空 JSON + 缺失提示图）
- **漫漫 / ManMan** 品牌待补（Task I 建议，Phase 2 后期）
- 实物色差仅有 30 个色号的测量方法，没有完整测量数据

---

## 3. JSON Schema（每个 `<brand>_<diameter>mm.json` 通用）

每个色号一个对象，所有 brand × diameter 文件共用此 schema：

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
  "stock_status": "common",        // common / rare / discontinued
  "price_per_100g": 8.5,
  "price_per_1000pcs": 6.0,
  "buy_links": [
    { "platform": "淘宝", "url": "...", "shop_name": "...", "captured_at": "2026-05-25" }
  ],
  "notes": ""
}
```

**字段含义见 `colormap/README.md` 详细文档。**

---

## 4. 跨品牌对照（同豆径，CIEDE2000）

`crossref_full.csv`（7759 行）字段：
- `source_brand` / `source_diameter` / `source_code`
- `target_brand` / `target_code`
- `ciede2000`（色差，越小越接近）
- `rank`（1-3，每个 source 列出最相似的 Top 3）

**业务用途**：
- 后端的"跨品牌图纸转换"功能（Phase 2/3 可选）
- 你想用 MARD M01 但国内缺货时，查 Hama / Artkal 哪个色号最接近

**不跨豆径对照**——物理上不能混拼。

---

## 5. 国内市场数据（Task I 产出）

| 文件 | 数据量 | 用途 |
|------|--------|------|
| `bead_skus_cn.csv` | 102 SKU | 1688 / 淘宝 / 京东实际商品 + 价格 + 月销量 |
| `chinese_color_aliases.json` | 120 个官方色号 → N 个中文别名 | 前端 UI 色号搜索"奶白""腮红粉"等口语词支持（PRD §7.5） |
| `china_market_status_overrides.json` | 55 个色号标注 | 覆盖默认 stock_status，加 `china_market_status`（active / low_stock / discontinued_cn / new_release）|
| `xhs_color_mentions.csv` | 50 条 public web 笔记 | 小红书博主提到的色号 + URL + 互动数 |
| `xhs_kol_preferences.md` | 摘要 | Top KOL 的色卡偏好 + 避雷帖 |
| `brand_popularity_cn.md` | 摘要 | 国内品牌销量推断的热度排序 |
| `physical_vs_screen_delta.md` | 30 色号测量方法 | 实物熨烫后 vs 屏幕 HEX 色差观察 |
| `community_insights.md` | 摘要 | 百度贴吧 / B 站社区用户认知 |
| `competitor_palette_reverse.md` | 8 个工具反查 | 已上场拼豆工具用什么色卡 + 多少色号 |
| `cn_supply_status.md` | 摘要 | 国内供应链状态（缺货 / 新色 / 停产）|

---

## 6. 后端调用入口（task 3 已实现）

```python
from pindou.colormap.loader import load_palette
from pindou.colormap.matcher import match_nearest_color

# 加载色卡（首次 load，之后内存缓存）
palette = load_palette(brand="mard", diameter_mm=5.0)
# palette: list[ColorRef]，每个有 code / name_cn / hex / rgb / lab 等字段

# 给定 RGB 找最近色卡色号（CIEDE2000）
matched = match_nearest_color(rgb=(255, 200, 180), palette=palette)
# matched: ColorRef，最接近的色号
```

`PatternBuilder.build()` 内部就是这样用 palette 做量化的（`06_backend/pindou/pattern/quantize.py`）。

---

## 7. 数据更新流程

色卡数据**不在 SQL 表**（Phase 2 task 4 review 决策，PRD §6.1）：
- 数据相对静态，写入由 `build_full_bead_db.py` / `build_china_deep_dive_outputs.py` 等脚本批量执行
- 业务运行时只读 + 内存缓存
- 更新数据：跑构建脚本 → 覆盖 JSON / CSV → 后端服务重启加载新缓存

**何时迁 SQL 表**（Phase 4+ 触发条件）：
- 需要实时库存 / 价格展示
- 多品牌 SKU 总数 > 5000 行内存压力
- 后台需要动态增删 SKU 不重启服务

---

## 8. 数据源留痕

所有外部数据源记录在 `00_meta/data_sources.md`。包括：
- Hama official / Perler official / Artkal official
- Bitbead / Pixel Pattern / get-colors-from-beans
- 1688 / 淘宝 / 京东公开页面
- 小红书公开搜索页

---

## 9. 谁该读这份索引

| 角色 | 读这份索引的场景 |
|------|----------------|
| **Claude（对话里）** | 用户问"MARD 5mm 多少色 / 黄豆豆色卡在哪 / 中文色名映射怎么用" → 先读 INDEX 定位文件再读详情 |
| **Codex（后端实现）** | 实现新色卡相关功能 → 读 INDEX 找数据 schema 和文件路径 |
| **Gemini（前端实现）** | 实现色号搜索 UI → 读 INDEX 找 `chinese_color_aliases.json` 怎么用 |
| **用户** | 自己想知道数据状态 / 哪些 brand 缺数据 / 下一步该爬什么 |
