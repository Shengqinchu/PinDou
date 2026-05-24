# Task D — 色卡数据库（先启动）

**Status**: pending
**Owner**: Codex
**Priority**: 高
**Estimated**: 1-2 天
**依赖**: 无
**被依赖**: 任务 B 算法横评、任务 C AI PoC 都需要 MARD/COCO palette

---

## 背景
后端量化算法需要"目标色卡"作 palette。如果色卡数据不全 / HEX 不准 / 价格缺失，整个产品 BOM 估价和材料清单都跑不起来。本任务是 B 和 C 的依赖项，**先启动**。

## 目标
建立完整、结构化、可后端直接消费的 MARD + COCO 色卡数据库 + 跨色卡可替代对照表。

---

## 任务步骤

### 步骤 1：MARD 全色号采集
来源：
- MARD 官方网站 / 京东 / 淘宝旗舰店 / 拼豆论坛 / 小红书博主整理表
- 至少交叉验证 2 个来源

字段（per 色号）：
```json
{
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

输出：`01_research/colormap/mard.json`

### 步骤 2：COCO 全色号采集（同上字段）
输出：`01_research/colormap/coco.json`

### 步骤 3：跨色卡对照表
对每个 MARD 色号，用 **CIEDE2000** 找出 COCO 中色差最小的前 3 个候选（带色差值）。反向同理。

输出：`01_research/colormap/crossref.csv`
字段：`source_brand, source_code, target_brand, target_code, ciede2000, rank`

### 步骤 4：可视化 palette
生成色卡图：
- `01_research/colormap/mard_palette.png`（按色系分组排列）
- `01_research/colormap/coco_palette.png`

### 步骤 5：写 README
`01_research/colormap/README.md`：
- 数据来源（每个字段哪里来）
- 抓取日期
- 字段定义（schema）
- 更新方式（如何重新采集 / 增量更新）
- 已知缺漏（哪些色号查不到价格 / HEX 不可信）

---

## 工具建议
- 颜色空间转换：`colormath` / `colour-science` Python 库
- CIEDE2000 计算：`colormath.color_diff.delta_e_cie2000`
- 爬取：`requests` + `BeautifulSoup`；动态页用 `playwright`
- **不要爬取需要登录的页面 / 不要爬取明确禁止爬取的站点**

## 数据源留痕
每个数据源在 `00_meta/data_sources.md` 加一条：
- URL
- 抓取日期
- 用途（MARD 色号 / 价格 / HEX）
- 数据格式（HTML / JSON）
- 许可状态（公开 / 商用许可不明）

---

## 输出位置
- `01_research/colormap/mard.json`
- `01_research/colormap/coco.json`
- `01_research/colormap/crossref.csv`
- `01_research/colormap/mard_palette.png`
- `01_research/colormap/coco_palette.png`
- `01_research/colormap/README.md`

## 验收标准
- [ ] MARD 色号 ≥ 280 个（市场上一般 300 左右，缺失部分注明原因）
- [ ] COCO 色号 ≥ 80 个
- [ ] 所有色号 HEX 至少 2 个来源交叉验证
- [ ] 跨色卡对照表 100% 覆盖（每个色号都有 Top-3 对应）
- [ ] 至少 80% 色号有价格数据
- [ ] palette 可视化图清晰可读
- [ ] README 字段定义完整，schema 可被后端直接消费

## 不要做
- ❌ 不要爬取需登录页面
- ❌ 不要 fork 别人的色卡仓库直接占有版权（标明出处 + 标注 "数据二次整理"）
- ❌ 不要把价格当成真实成交价（注明"采集时挂牌价"）
