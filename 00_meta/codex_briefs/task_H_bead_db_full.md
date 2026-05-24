# Task H — 全品牌全规格豆系信息库

**Status**: completed (Codex @ 2026-05-24) — 产出见下方“完成产出”
**Owner**: Codex
**Priority**: 高（Phase 1 启动前必须完成）
**Estimated**: 3-4 天
**依赖**: Task D 完成的 MARD + COCO 基线作为起点
**被依赖**: Phase 1 PRD（PatternBuilder 接口需要全品牌 palette）

---

## 完成产出

- 生成脚本：`01_research/colormap/build_full_bead_db.py`
- 数据 README / 覆盖矩阵 / schema：`01_research/colormap/README.md`
- 跨品牌同豆径对照：`01_research/colormap/crossref_full.csv`
- MARD：`01_research/colormap/mard_2_6mm.json`, `01_research/colormap/mard_5mm.json`, `01_research/colormap/mard_10mm.json`
- COCO：`01_research/colormap/coco_2_6mm.json`, `01_research/colormap/coco_5mm.json`, `01_research/colormap/coco_10mm.json`
- Hama：`01_research/colormap/hama_2_5mm.json`, `01_research/colormap/hama_5mm.json`, `01_research/colormap/hama_10mm.json`
- Perler：`01_research/colormap/perler_5mm.json`
- Artkal：`01_research/colormap/artkal_2_6mm.json`, `01_research/colormap/artkal_5mm.json`, `01_research/colormap/artkal_10mm.json`
- 其他国产：`01_research/colormap/other_huangdoudou_5mm.json`, `01_research/colormap/other_mixiaowo_5mm.json`, `01_research/colormap/other_panpan_5mm.json`
- 可视化：`01_research/colormap/*_palette.png`
- 数据源留痕：`00_meta/data_sources.md`
- Phase 1 PRD 衔接建议 / schema 问题：`00_meta/codex_briefs/_questions_for_user.md`

---

## 背景
ADR-002 修订后：信息库要全，产品功能可收敛。Task D 完成了 MARD（291 色）+ COCO（80 色）的 5mm 中豆基线；Task H 把这个数据库扩展到全品牌全规格，作为 Phase 1 + 后期所有"切品牌 / 切豆径 / 跨品牌图纸"功能的底层数据资产。

**前置阅读**（必读）：
1. `01_research/colormap/README.md`（Task D 已建立的 schema）
2. `01_research/tech/perler_bead_domain_notes.md`（拼豆领域知识、豆系尺寸知识）
3. `04_architecture/ADRs/ADR-002-color-palette.md`（修订版决策）
4. `04_architecture/ADRs/ADR-008-preview-pattern-split.md`（PatternBuilder 对 palette 的需求）
5. `04_architecture/ADRs/ADR-009-private-asset-handling.md`（不入 git 的素材规则，本任务不应触及）
6. `01_research/compliance/compliance_checklist.md` 中"商标边界"一节（品牌名 / Logo 使用红线）

## 目标
建立完整、结构化、可后端直接消费的**多品牌 × 多豆径**色卡信息库 + 跨品牌跨豆径对照表。

---

## 调研范围

### 品牌矩阵
| 品牌 | 国别 | 优先级 | 备注 |
|------|------|--------|------|
| MARD | 国产 | P0 已有 | Task D 已完成 5mm，需补 2.6mm / 10mm |
| COCO | 国产 | P0 已有 | Task D 已完成 5mm，需补 2.6mm / 10mm |
| Hama | 丹麦 | P1 | Midi 5mm + Mini 2.5mm + Maxi 10mm，国际主流 |
| Perler | 美国 | P1 | 5mm 类似 Hama，美国主流 |
| Artkal | 国产 | P1 | 2.6mm 小豆国内最受欢迎 |
| 其他国产 | 中国 | P2 | 调研 1688 / 淘宝 Top 3 其他品牌，列出但不强求字段全 |

### 豆径矩阵
- 2.5mm / 2.6mm Mini（小豆）
- 5mm Midi（中豆）
- 10mm Maxi（大豆）

注意：Hama 是 2.5mm，Artkal / Perler Mini 是 2.6mm，**这是不同的物理规格不能混用**——记得在 schema 里区分。

### 每个 品牌 × 豆径 组合的字段（per 色号）
继承 Task D 的 schema 并扩展：
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
  "stock_status": "common | rare | discontinued",
  "price_per_100g": 8.5,
  "price_per_1000pcs": 6.0,
  "buy_links": [
    { "platform": "淘宝", "url": "...", "shop_name": "...", "captured_at": "2026-05-25" }
  ],
  "notes": ""
}
```

## 任务步骤

### 步骤 1：MARD / COCO 补豆径
Task D 已完成 5mm。本步骤把 MARD / COCO 的 2.6mm 和 10mm 色号补全（若该品牌该豆径不存在则注明，不强求）。

### 步骤 2：Hama 全色号采集（3 豆径）
来源：Hama 官方网站 / 京东 Hama 旗舰店 / 国际拼豆社区资源。

### 步骤 3：Perler 全色号（5mm）
来源：Perler 官方 / 美区零售 / 二级整理表。

### 步骤 4：Artkal 全色号（2.6mm 优先，5mm 次之）
来源：Artkal 官方 / 淘宝 / 1688。

### 步骤 5：其他国产
1688 / 淘宝搜"拼豆"销量 Top 30 店铺，识别 5+ 非主流品牌，记录品牌名 + 字段尽可能全（允许缺失字段，注明"待补"）。

### 步骤 6：跨品牌 × 跨豆径对照表（关键）
对每个 brand × diameter × color，用 **CIEDE2000** 找出其他 brand × **同一豆径** 中色差最小的前 3 个候选（跨豆径不做对照，物理上不能混用）。

输出：`01_research/colormap/crossref_full.csv`
字段：`source_brand, source_diameter, source_code, target_brand, target_code, ciede2000, rank`

### 步骤 7：可视化 palette
为每个 brand × diameter 组合生成 palette 图（按色系分组）：
- `01_research/colormap/<brand>_<diameter>mm_palette.png`

### 步骤 8：更新 README
扩展 `01_research/colormap/README.md`：
- 新增品牌 / 豆径覆盖矩阵表
- 每个品牌的数据源 + 抓取日期 + 可信度
- schema 字段定义更新
- 缺漏标注（哪些品牌 × 豆径组合查不到完整数据）
- 商标使用边界提醒（基于 Task F 合规结论）

## 工具复用
- 沿用 Task D 的 `01_research/colormap/build_colormap.py` 框架
- CIEDE2000 计算：`colormath.color_diff.delta_e_cie2000`
- 爬取：`requests` + `BeautifulSoup`，动态页 `playwright`
- 不要爬取需登录页面 / 明确禁止爬取的站点

## 数据源留痕
每个数据源在 `00_meta/data_sources.md` 加一条（按现有 schema）。

---

## 输出位置
- 数据：
  - `01_research/colormap/mard_2_6mm.json` / `mard_5mm.json`（已有）/ `mard_10mm.json`
  - `01_research/colormap/coco_*.json`
  - `01_research/colormap/hama_*.json`
  - `01_research/colormap/perler_*.json`
  - `01_research/colormap/artkal_*.json`
  - `01_research/colormap/other_<brand>_*.json`
- 跨品牌对照：`01_research/colormap/crossref_full.csv`
- 可视化：`01_research/colormap/*_palette.png`
- README：更新 `01_research/colormap/README.md`

## 验收标准
- [ ] MARD 三豆径覆盖完整
- [ ] COCO 三豆径覆盖完整（如该品牌不出某豆径，README 注明）
- [ ] Hama 三豆径覆盖完整（Hama 是国际主流，资料相对全）
- [ ] Perler 5mm 完整
- [ ] Artkal 2.6mm 完整
- [ ] 至少 3 个其他国产品牌的 5mm 字段（允许字段不全，注明）
- [ ] 跨品牌对照表（同豆径）覆盖所有 brand-color 组合
- [ ] 每个 brand × diameter 有可视化 palette 图
- [ ] README 覆盖矩阵表清晰、字段定义完整、数据源可追溯

## 不要做
- ❌ 不要把品牌 Logo / 官方宣传图入 git（商标边界，参考 Task F 合规结论）
- ❌ 不要爬取需登录页面
- ❌ 不要把价格当成"必准"（注明"采集时挂牌价"）
- ❌ 不要跨豆径做色卡对照（物理上不能混拼）
- ❌ 不要遗漏 schema 字段（缺失也要保留 key + 写 null + 注明原因）

## 与 Phase 1 PRD 的衔接
任务完成后，`PatternBuilder.build(preview, size, brand, bead_diameter)` 接口在 Phase 1 PRD 中将直接消费本任务输出。所以本任务的 JSON schema **必须稳定**（命名 / 字段 / 单位）。任务过程中如发现 schema 需要扩展，先在 `_questions_for_user.md` 提出。
