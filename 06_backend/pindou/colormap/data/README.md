# PinDou 色卡数据包

本目录是生产色卡的单一真相源。`01_research/colormap/` 保留生成脚本、来源说明和研究产物；运行时与前端构建期派生资源都应优先从本目录读取，避免手工维护第二份色卡。

## 加载规则

- 后端 `loader.py` 通过 `palette_filename(brand, bead_diameter_mm)` 拼出 `{brand}_{diameter}mm.json`，例如 `MARD + 5.0` 对应 `mard_5mm.json`。
- 旧版 `mard.json` / `coco.json` 是 legacy 基线，缺少 `bead_diameter_mm`。新功能应优先使用带豆径的 `*_5mm.json` / `*_2_6mm.json` 文件。
- `mard_10mm.json` / `coco_10mm.json` / `artkal_10mm.json` 为空占位，表示暂无可信结构化色值；禁止凭空补色值。

## 后端完整版字段

每个非空 JSON 行应包含：

- `brand`
- `bead_diameter_mm`
- `code`
- `name_cn`
- `name_en`
- `hex`
- `rgb`
- `lab`
- `category`
- `stock_status`
- `price_per_100g`
- `price_per_1000pcs`
- `price_confidence`
- `buy_links`
- `notes`
- `verified_sources`

价格、库存、来源字段来自公开线索，置信度不等同实时采购报价。品牌名仅作兼容色号说明，不代表官方授权。

## 前端精简字段

Web 编辑器的“全部颜色”静态资源由 `05_web/scripts/build-colormap-assets.mjs` 从本目录派生。本轮仅导出 MARD 5mm：

- `brand`
- `code`
- `name_cn`
- `hex`
- `rgb`
- `category`
- `bead_diameter_mm`

前端不得手工维护第二份色卡；如本目录更新，应重新执行前端 `npm run build:colormap`。

## UI 暴露边界

当前产品层只暴露 MARD 5mm。COCO / Hama / Perler / Artkal / 国产其他品牌保留为底层数据与未来扩展，不在本轮 Web UI 中提供品牌或豆径切换。
