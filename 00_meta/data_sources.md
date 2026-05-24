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

### GitHub Skills 候选仓库扫描
- URL / 标识：GitHub API + 仓库 README；核心仓库包括 alirezarezvani/claude-skills、phuryn/pm-skills、nextlevelbuilder/ui-ux-pro-max-skill、mattpocock/skills、github/spec-kit、assafelovic/gpt-researcher、adr/madr 等
- 抓取 / 拉取日期：2026-05-24
- 用途：Task G GitHub Skills 候选筛选；记录 license、Star/Fork、最近更新、README 示例、`SKILL.md` 目录结构、Top 3 推荐与避雷清单
- 数据格式：GitHub REST API JSON / README Markdown / 仓库目录树
- 许可状态：仅纳入 MIT / Apache-2.0 / MIT-0 / CC0-1.0 / MIT OR CC0-1.0 等宽松协议；license unknown 或 NC/ND/SA 仓库列入避雷
- 存储位置：`01_research/tech/skills_candidates.md`
- 责任人：Codex

### Task A GitHub repository metadata
- URL / 标识：GitHub API + 仓库 README；包括 WuZongWei6/Pixelization、tencent-ailab/IP-Adapter、Comfy-Org/ComfyUI、AUTOMATIC1111/stable-diffusion-webui、lllyasviel/ControlNet、Mikubill/sd-webui-controlnet、cubiq/ComfyUI_IPAdapter_plus、sedthh/pyxelate、Tezumie/Image-to-Pixel、ImageOptim/libimagequant、gametorch/image_to_pixel_art_wasm、maxcleme/beadifier 等
- 抓取 / 拉取日期：2026-05-24
- 用途：现有拼豆 / 像素化 / AI 工作流开源生态拆解，记录 Star、协议、更新时间、技术栈
- 数据格式：GitHub API JSON / GitHub README Markdown
- 许可状态：各仓库不同，报告内逐项标注；GPL / AGPL / 非商用需商用风险提示
- 存储位置：`01_research/tech/github_landscape.md`
- 责任人：Codex

### Task A Web bead/pixel tools
- URL / 标识：https://makebead.com/ ; https://bitbead.pomodiary.com/ ; https://www.beadmapper.com/ ; https://beadpattern.net/zh ; https://simplepixelart.com/convert ; https://pixel-perler-ai.com/
- 抓取 / 拉取日期：2026-05-24
- 用途：Web 端拼豆 / 像素化工具功能、算法、导出、商业化模式拆解
- 数据格式：公开网页 HTML
- 许可状态：公开页面；商用复用许可未知，仅作竞品研究引用
- 存储位置：`01_research/tech/existing_tools.md`
- 责任人：Codex

### Task A Chinese mini-program/app/product references
- URL / 标识：https://pindou.cn/ ; https://apps.apple.com/my/app/id6756865487 ; https://www.32r.com/app/143740.html ; https://digi.china.com/articles/20260420/202604201850740.html ; https://www.1004619.com/66750.html ; https://www.dian68.net/portal/article/index/cid/46/id/17362.html ; https://365-tools.cn/detail/40 ; https://dehumaker.cn/
- 抓取 / 拉取日期：2026-05-24
- 用途：中文拼豆工具 / 小程序竞品功能、商业化、色卡支持与用户流程拆解
- 数据格式：公开网页 HTML / App Store 页面
- 许可状态：公开页面；商用许可未知；仅作竞品研究引用
- 存储位置：`01_research/tech/existing_tools.md`
- 责任人：Codex

### 拼豆工具站定价页
- URL / 标识：https://www.pindou.online/pricing
- 抓取 / 拉取日期：2026-05-24
- 用途：Task E 竞品免费额度、会员价格、微信群激活码模式
- 数据格式：HTML
- 许可状态：公开；商用许可未知
- 存储位置：`01_research/competitor/business_models.md`
- 责任人：Codex

### App Store 拼豆 / 拼豆豆 / Perlypop
- URL / 标识：https://apps.apple.com/
- 抓取 / 拉取日期：2026-05-24
- 用途：Task E 订阅、去广告、评分与评论线索
- 数据格式：HTML
- 许可状态：公开；商用许可未知
- 存储位置：`01_research/competitor/business_models.md`
- 责任人：Codex

### BeadPattern / Fuse Bead Maker / Beadographer / PerlerBeadPattern pricing
- URL / 标识：https://beadpattern.net/zh ; https://www.fusebeadmaker.com/zh/pricing ; https://beadographer.com/about/ ; https://www.perlerbeadpattern.com/pricing
- 抓取 / 拉取日期：2026-05-24
- 用途：Task E 海外拼豆工具定价、免费额度、AI credit 模式参考
- 数据格式：HTML
- 许可状态：公开；商用许可未知
- 存储位置：`01_research/competitor/business_models.md`
- 责任人：Codex

### 小红书拼豆公开媒体转载样本
- URL / 标识：https://www.huxiu.com/article/4841619.html ; https://finance.sina.com.cn/jjxw/2026-04-04/doc-inhthwxz9657516.shtml
- 抓取 / 拉取日期：2026-05-24
- 用途：Task E 小红书拼豆账号 / 内容样本、内容形态归纳
- 数据格式：HTML
- 许可状态：公开转载；原小红书数据许可未知
- 存储位置：`01_research/competitor/xhs_accounts.md`, `08_growth/xhs_playbook.md`
- 责任人：Codex

### 小红书交易导流规则报道
- URL / 标识：https://www.ithome.com/0/837/049.htm
- 抓取 / 拉取日期：2026-05-24
- 用途：Task E 引流合规边界初稿；待 Task F 用平台官方规则交叉验证
- 数据格式：HTML
- 许可状态：公开新闻；需官方规则复核
- 存储位置：`08_growth/xhs_playbook.md`
- 责任人：Codex

---

## 类别建议（Codex 调研时分类）
- 色卡数据：MARD 官方、COCO 官方、电商列表
- 算法参考：GitHub 仓库、ECCV/CVPR 论文、博客教程
- 竞品数据：小程序竞品、Web 端工具、小红书账号
- 合规材料：法律条文、备案指南、平台规则
- AI 模型：HuggingFace、ModelScope、CivitAI
