# PinDou 色卡数据库

> 抓取 / 整理日期：2026-05-24  
> 覆盖：MARD 291 色、COCO 291 色  
> 产物：`mard.json`、`coco.json`、`crossref.csv`、`mard_palette.png`、`coco_palette.png`

## 结论

- MARD 与 COCO 都已整理为后端可直接消费的 JSON palette，每个色号包含 `hex`、`rgb`、`lab`、色系、库存状态、价格估算和来源链接。
- `crossref.csv` 已用 CIEDE2000 为每个 MARD 色号找出 COCO Top 3 近似色，并反向覆盖 COCO -> MARD。
- 当前版本适合 Phase 0 任务 B / C 做算法与 PoC 基准；进入生产前需要补一次实物色卡校验和电商 SKU 价格校验。

## 文件说明

| 文件 | 内容 | 记录数 |
|------|------|--------|
| `mard.json` | MARD 291 色结构化色卡 | 291 |
| `coco.json` | COCO 291 色结构化色卡 | 291 |
| `crossref.csv` | MARD <-> COCO Top 3 CIEDE2000 近似色 | 1746 |
| `mard_palette.png` | MARD 色卡可视化 | 291 色 |
| `coco_palette.png` | COCO 色卡可视化 | 291 色 |
| `build_colormap.py` | 可复现生成脚本 | Python 3 + Pillow |
| `_source_get-colors.json` | 原始公开抽取数据缓存 | 31 个色卡集合 |

## Schema

```json
{
  "brand": "MARD",
  "code": "A1",
  "name_cn": "MARD A1",
  "name_en": "MARD A1",
  "hex": "#FAF5CD",
  "rgb": [250, 245, 205],
  "lab": [95.8894, -4.7792, 21.0584],
  "category": "黄色系",
  "stock_status": "common",
  "price_per_100g": 10.8,
  "price_per_1000pcs": 1.08,
  "price_confidence": "low",
  "buy_links": [],
  "notes": "HEX from public palette extraction; official color name not confirmed. Price is a same-class public listing benchmark, not a live SKU quote.",
  "verified_sources": ["get-colors-from-beans", "pixel-beads/Bitbead or public tool pages"]
}
```

字段说明：

- `hex` / `rgb`：来自公开色卡抽取数据；HEX 全部规范化为大写。
- `lab`：由 sRGB D65 转 CIELAB，供 CIEDE2000 匹配使用。
- `category`：按 HSV 色相自动归类，供前端分组展示；不是官方分类。
- `stock_status`：出现在 221 色常用集的标为 `common`，只在 291 扩展集出现的标为 `rare`。
- `price_per_1000pcs`：挂牌价估算，不代表实时成交价。MARD 基准来自公开 221 色套装价；COCO 暂按同规格拼豆兼容价估算。
- `price_confidence`：当前均为 `low`，因为缺少可稳定抓取的单色 SKU。

## 数据来源与交叉验证

主源：

- `abearxiong/get-colors-from-beans`：MIT 标注的公开色卡抽取仓库，包含 `Mard-291` 与 `COCO-291`。

MARD 校验源：

- Pixel Beads MARD 色号页：页面标注 MARD 291 色，并展示色号与 HEX。
- Bitbead MARD 221 / 291 色卡页：展示 MARD palette、HEX 与跨品牌近似色。
- 豆豆工坊 MARD 221 色卡：可用于常用色集合与部分 HEX 对照。

COCO 校验源：

- 拼豆星球、Crapark 手册、BeadPattern 等公开工具均声明支持 COCO 色卡，但未稳定公开完整 HEX 表。
- 因此 COCO 的 HEX 当前以 `get-colors-from-beans` 为主，后续需用实体色卡或可授权数据源复核。

价格源：

- MARD 221 色套装公开页：221 色、每色约 1000 颗、整套 239 元，可折算约 1.08 元 / 1000 颗。
- 义乌购和 Rakuten 等页面可证明 1000 颗补充包存在，但价格区间波动大，暂不作为精确价格。

## 更新方式

1. 运行生成脚本：

```bash
python 01_research/colormap/build_colormap.py
```

2. 如需强制重新拉取源数据，删除 `_source_get-colors.json` 后再运行脚本。
3. 若新增官方色名或实测价格，优先在脚本里补映射表，不要手改生成后的 JSON。
4. 价格进入生产前应拆成单独 SKU 表，按 `brand + code + platform + captured_at` 存多条记录。

## 已知缺漏

- MARD / COCO 官方中文色名未在公开源中完整确认，当前 `name_cn/name_en` 仅作色号占位。
- COCO 291 色缺少第二个完整 HEX 数据源；Phase 1 前建议购买 / 拍摄实体色卡或联系工具作者授权。
- 价格是 2026-05-24 的公开挂牌估算，不能用于最终商城报价。
- HEX 来源是屏幕色卡，不等同于实体豆在自然光 / 熨烫后的观感；算法上线前需要实物校色。
