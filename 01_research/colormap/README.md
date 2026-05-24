# PinDou 色卡数据库

> Phase 0 Task D / H  
> 更新日期：2026-05-24  
> 口径：信息库尽量全，产品默认仍按 ADR-002 收敛到 MARD 5mm。

## 结论

- Task D 的 `mard.json` / `coco.json` 保留作为旧版基线；Task H 新增 `brand + bead_diameter_mm` 维度，后端应优先消费 `*_5mm.json` / `*_2_6mm.json` 这批新文件。
- `crossref_full.csv` 已按 CIEDE2000 生成同豆径跨品牌 Top 3 近邻。严格不做 2.5mm、2.6mm、5mm、10mm 之间的跨径匹配。
- 官方普遍不公开 HEX/RGB。数据库把官方可确认的规格、系列、商品样本和第三方 HEX 工具页拆开记录，进入生产前仍需要实物色卡或授权色卡复核。
- 品牌名仅作兼容色号描述，不使用品牌 Logo，不写“官方 / 授权 / 联名”。

## 覆盖矩阵

| 品牌 | 2.5mm | 2.6mm | 5mm | 10mm | 说明 |
|------|-------|-------|-----|------|------|
| MARD | - | 221 色 | 291 色 | 空文件 | 2.6mm 仅确认 221 色公开商品证据；10mm 未找到可靠公开色卡 |
| COCO | - | 291 色 | 291 色 | 空文件 | 2.6mm/5mm 使用公开工具色卡；官方完整色卡仍缺 |
| Hama | 89 色系参考 | - | 89 色 | 89 色系参考 | 官方确认 Mini/Midi/Maxi 共用色号体系，但各尺寸覆盖不同；当前文件是色号体系参考，不等同订货清单 |
| Perler | - | - | 117 色 | - | 5mm 使用 Bitbead 规范化 P-code + Perler 官方规格/价格样本交叉说明 |
| Artkal | - | 221 色 | 201 色 | 空文件 | 2.6mm 用 Artkal Mini/M 系列公开 HEX；5mm 用 Pixel Pattern S 系列；10mm X 系列存在但缺结构化 HEX |
| 黄豆豆 | - | - | 291 色 | - | 其他国产公开色卡，需人工确认品牌和供货 |
| 咪小窝 | - | - | 287 色 | - | 原始源声称 290，去重后 287 |
| 盼盼 | - | - | 286 色 | - | 原始源声称 289，去重后 286 |

## 文件说明

| 文件 | 内容 |
|------|------|
| `mard_5mm.json` / `coco_5mm.json` | Phase 1 默认候选色卡，带 `bead_diameter_mm` |
| `mard_2_6mm.json` / `coco_2_6mm.json` | 小豆候选色卡，COCO 置信度低于 MARD |
| `hama_2_5mm.json` / `hama_5mm.json` / `hama_10mm.json` | Hama 色号体系参考，HEX 为第三方近似 |
| `perler_5mm.json` | Perler 5mm 色卡参考 |
| `artkal_2_6mm.json` / `artkal_5mm.json` / `artkal_10mm.json` | Artkal 2.6mm / 5mm / 10mm 数据，10mm 暂为空 |
| `other_*_5mm.json` | 其他国产公开色卡候选 |
| `crossref_full.csv` | 同豆径跨品牌 Top 3 CIEDE2000 近邻 |
| `*_palette.png` | 每个 brand × diameter 的可视化色卡，空数据会生成缺失提示图 |
| `build_colormap.py` | Task D MARD/COCO 基线生成脚本 |
| `build_full_bead_db.py` | Task H 全品牌/豆径生成脚本 |

## Schema

每个 JSON 文件是颜色数组，字段保持 Task D 结构并新增 `bead_diameter_mm`：

```json
{
  "brand": "MARD",
  "bead_diameter_mm": 5.0,
  "code": "A1",
  "name_cn": "Light Beige",
  "name_en": "Light Beige",
  "hex": "#FAF5CD",
  "rgb": [250, 245, 205],
  "lab": [96.0124, -4.7145, 19.8987],
  "category": "黄色系",
  "stock_status": "common",
  "price_per_100g": 10.8,
  "price_per_1000pcs": 1.08,
  "price_confidence": "low",
  "buy_links": [],
  "notes": "HEX/source/price confidence notes...",
  "verified_sources": []
}
```

字段说明：

- `bead_diameter_mm`：物理豆径。2.5mm 与 2.6mm 分开，不能混拼。
- `hex` / `rgb` / `lab`：屏幕色值，用于算法匹配，不等同实物熨烫后观感。
- `category`：按 HSV 自动归类，方便前端分组，不是官方分类。
- `stock_status`：`common` / `rare` / `discontinued`；公开源无法判断时先按来源集合保守标注。
- `price_per_1000pcs`：保留 Task D 字段，但 Task H 已出现 CNY / USD / EUR 混合来源，生产前建议拆成带币种的 SKU 价格表。
- `buy_links`：来源或样本页，不代表推荐购买渠道。

`crossref_full.csv` 字段：

```csv
source_brand,source_diameter,source_code,target_brand,target_code,ciede2000,rank
```

## 数据来源与可信度

| 来源 | 用途 | 可信度 |
|------|------|--------|
| `abearxiong/get-colors-from-beans` | MARD / COCO / 其他国产公开 HEX 源 | 中；MIT 仓库，但非品牌官方 |
| Pixel Pattern Color Converter | MARD 英文名、Artkal S 表、公开 HEX/RGB 表 | 中；页面说明部分来自官方 PDF/OCR，仍需实物复核 |
| Bitbead color pages | Hama / Perler / Artkal Mini 结构化 HEX | 中；适合算法 PoC，不应宣称官方 |
| Hama 官方页面 | Mini 2.5mm、Midi 5mm、Maxi 10mm 与共用色号体系 | 高；但官方未给 HEX |
| Perler 官方商品页 / 色卡 PDF | 5mm 实际尺寸、SKU、价格样本、官方色卡参考 | 高；但未给机器可读 HEX |
| Artkal 官方页面/PDF | 系列、尺寸、X 10mm 存在性 | 高；不同页面色数有版本冲突 |
| 电商/工具页公开提及 | MARD / COCO 2.6mm、其他国产品牌存在性 | 低到中；只能做线索 |

## 已知缺漏

- MARD / COCO 10mm 未找到可靠公开色卡，已保留空 JSON 和缺失提示图。
- Hama Mini/Maxi 当前使用共享色号体系参考；每个尺寸的真实在售色号集合还需要从官方 PDF / SKU 页进一步提取。
- Perler 官方 SKU 与 Bitbead P-code 没有完整交叉表；当前 `perler_5mm.json` 更适合算法匹配，不适合作为最终采购 SKU 表。
- Artkal 10mm X 系列确认存在 15 色，但没有结构化 HEX 表；`artkal_10mm.json` 暂为空。
- 价格字段没有币种，Task H 已暴露 schema 问题，见 `00_meta/codex_briefs/_questions_for_user.md`。

## 更新方式

1. 生成 Task D 基线：

```bash
python 01_research/colormap/build_colormap.py
```

2. 生成 Task H 全库：

```bash
python 01_research/colormap/build_full_bead_db.py
```

3. 若进入 Phase 1 PRD，优先把价格拆成单独 SKU 表：`brand + bead_diameter_mm + code + platform + currency + captured_at`。

## 商标边界

MARD、COCO、Hama、Perler、Artkal 等名称只用于“兼容色号 / 色卡对照 / 图纸导出”的描述性说明。产品页、Logo、域名、主视觉和广告文案不得使用“官方、授权、联名、旗舰”等容易造成混淆的表达。
