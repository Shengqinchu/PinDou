# 外部数据源清单

> 记录所有从外部系统拉取或参考的数据，便于追溯、复现、合规。
> 添加时必须填：来源 / 抓取日期 / 用途 / 许可状态。

## 模板
```
### [来源名]
- URL / 标识：
- 抓取 / 拉取日期：
- 用途：
- 数据格式：
- 许可状态：（公开 / 商用许可 / 需联系 / 未知）
- 存储位置：
- 责任人：（用户 / Codex / Gemini）
```

## 当前清单

（Phase 0 启动时为空，由 Codex 在调研过程中追加）

### abearxiong/get-colors-from-beans
- URL / 标识：https://git.xiongxiao.me/abearxiong/get-colors-from-beans
- 抓取 / 拉取日期：2026-05-24
- 用途：MARD-291、COCO-291 原始 HEX 色卡；生成 `mard.json`、`coco.json`、`crossref.csv`
- 数据格式：JSON / HTML extraction
- 许可状态：MIT（仓库 README 标注）
- 存储位置：`01_research/colormap/_source_get-colors.json`
- 责任人：Codex

### Pixel Beads MARD color chart
- URL / 标识：https://www.pixel-beads.com/zh/mard-bead-color-chart
- 抓取 / 拉取日期：2026-05-24
- 用途：MARD 291 色号与 HEX 交叉校验
- 数据格式：HTML
- 许可状态：公开；商用许可未知
- 存储位置：`01_research/colormap/README.md`
- 责任人：Codex

### Bitbead MARD / brand palettes
- URL / 标识：https://bitbead.pomodiary.com/colors
- 抓取 / 拉取日期：2026-05-24
- 用途：MARD 221 / 291 色卡规模、HEX 与跨品牌近似色逻辑交叉参考
- 数据格式：HTML
- 许可状态：公开；商用许可未知
- 存储位置：`01_research/colormap/README.md`
- 责任人：Codex

### 豆豆工坊 MARD 色卡
- URL / 标识：https://www.doudougongfang.com/kb/beads/mard-palette
- 抓取 / 拉取日期：2026-05-24
- 用途：MARD 221 常用色集合与部分 HEX 交叉校验
- 数据格式：HTML
- 许可状态：公开；商用许可未知
- 存储位置：`01_research/colormap/README.md`
- 责任人：Codex

### 拼豆工具站 MARD 221 套装价
- URL / 标识：https://www.pindou.online/shop
- 抓取 / 拉取日期：2026-05-24
- 用途：MARD 221 色、每色约 1000 颗、239 元整套的价格估算基准
- 数据格式：HTML
- 许可状态：公开；商用许可未知
- 存储位置：`01_research/colormap/README.md`
- 责任人：Codex

### 拼豆星球 COCO 色卡支持说明
- URL / 标识：https://pindou.cn/
- 抓取 / 拉取日期：2026-05-24
- 用途：COCO 色卡市场存在性和工具支持交叉参考
- 数据格式：HTML
- 许可状态：公开；商用许可未知
- 存储位置：`01_research/colormap/README.md`
- 责任人：Codex

### Crapark 拼豆色卡说明书
- URL / 标识：https://pd.crapark.com/manual-tablet.html
- 抓取 / 拉取日期：2026-05-24
- 用途：COCO 色卡工具支持与数据来源说明参考
- 数据格式：HTML
- 许可状态：公开；商用许可未知
- 存储位置：`01_research/colormap/README.md`
- 责任人：Codex

### 义乌购 MARD / 同规格补充包
- URL / 标识：https://wap.yiwugo.com/products/985118873
- 抓取 / 拉取日期：2026-05-24
- 用途：1000 粒补充包存在性与价格区间参考
- 数据格式：HTML
- 许可状态：公开；商用许可未知
- 存储位置：`01_research/colormap/README.md`
- 责任人：Codex

### Rakuten COCO 2.6mm 拼豆商品页
- URL / 标识：https://www.rakuten.com.tw/shop/cwow1/product/1809457/
- 抓取 / 拉取日期：2026-05-24
- 用途：COCO 与 MARD 兼容规格、套装存在性参考
- 数据格式：HTML
- 许可状态：公开；商用许可未知
- 存储位置：`01_research/colormap/README.md`
- 责任人：Codex

### scikit-learn MiniBatchKMeans documentation
- URL / 标识：https://sklearn.org/stable/modules/generated/sklearn.cluster.MiniBatchKMeans.html
- 抓取 / 拉取日期：2026-05-24
- 用途：Task B K-means 量化实现参考
- 数据格式：HTML documentation
- 许可状态：BSD-3-Clause（scikit-learn 项目许可）
- 存储位置：`01_research/tech/algorithm_impls/quantize_core.py`
- 责任人：Codex

### Pillow Image.quantize documentation
- URL / 标识：https://pillow.readthedocs.io/en/stable/reference/Image.html
- 抓取 / 拉取日期：2026-05-24
- 用途：Task B Median-cut / Octree 量化实现参考
- 数据格式：HTML documentation
- 许可状态：HPND（Pillow 项目许可）
- 存储位置：`01_research/tech/algorithm_impls/quantize_core.py`
- 责任人：Codex

### scikit-image metrics documentation
- URL / 标识：https://scikit-image.org/docs/stable/api/skimage.metrics.html
- 抓取 / 拉取日期：2026-05-24
- 用途：Task B PSNR / SSIM 指标实现参考
- 数据格式：HTML documentation
- 许可状态：BSD-3-Clause（scikit-image 项目许可）
- 存储位置：`01_research/tech/algorithm_impls/quantize_core.py`
- 责任人：Codex

### CIEDE2000 implementation notes
- URL / 标识：https://hajim.rochester.edu/ece/sites/gsharma/ciede2000/
- 抓取 / 拉取日期：2026-05-24
- 用途：Task B / D CIEDE2000 色差公式实现参考
- 数据格式：HTML / PDF notes
- 许可状态：公开学术资料；商用许可未知
- 存储位置：`01_research/tech/algorithm_impls/quantize_core.py`, `01_research/colormap/build_colormap.py`
- 责任人：Codex

---

## 类别建议（Codex 调研时分类）
- 色卡数据：MARD 官方、COCO 官方、电商列表
- 算法参考：GitHub 仓库、ECCV/CVPR 论文、博客教程
- 竞品数据：小程序竞品、Web 端工具、小红书账号
- 合规材料：法律条文、备案指南、平台规则
- AI 模型：HuggingFace、ModelScope、CivitAI
