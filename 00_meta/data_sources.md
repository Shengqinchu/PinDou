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

### 中华人民共和国个人信息保护法
- URL / 标识：https://www.cac.gov.cn/2021-08/20/c_1631050028355286.htm
- 抓取 / 拉取日期：2026-05-24
- 用途：Task F 人像上传、敏感个人信息、单独同意、删除权、跨境提供规则
- 数据格式：HTML
- 许可状态：官方公开法律文本
- 存储位置：`01_research/compliance/compliance_checklist.md`
- 责任人：Codex

### 促进和规范数据跨境流动规定
- URL / 标识：https://www.cac.gov.cn/2024-03/22/c_1712776611775634.htm
- 抓取 / 拉取日期：2026-05-24
- 用途：Task F 日本服务器跨境数据、标准合同 / 认证 / 安全评估阈值判断
- 数据格式：HTML
- 许可状态：官方公开部门规章
- 存储位置：`01_research/compliance/compliance_checklist.md`
- 责任人：Codex

### 个人信息出境标准合同办法
- URL / 标识：https://www.cac.gov.cn/2023-02/24/c_1678884831596384.htm
- 抓取 / 拉取日期：2026-05-24
- 用途：Task F 个人信息出境标准合同适用与备案参考
- 数据格式：HTML
- 许可状态：官方公开部门规章
- 存储位置：`01_research/compliance/compliance_checklist.md`
- 责任人：Codex

### 生成式人工智能服务管理暂行办法
- URL / 标识：https://www.cac.gov.cn/2023-07/13/c_1690898327029107.htm
- 抓取 / 拉取日期：2026-05-24
- 用途：Task F AIGC 服务定义、提供者义务、内容标识、安全评估 / 算法备案
- 数据格式：HTML
- 许可状态：官方公开部门规章
- 存储位置：`01_research/compliance/compliance_checklist.md`
- 责任人：Codex

### 互联网信息服务深度合成管理规定
- URL / 标识：https://www.gov.cn/zhengce/zhengceku/2022-12/12/content_5731431.htm
- 抓取 / 拉取日期：2026-05-24
- 用途：Task F AI 生成图片标识、深度合成服务治理参考
- 数据格式：HTML
- 许可状态：官方公开部门规章
- 存储位置：`01_research/compliance/compliance_checklist.md`
- 责任人：Codex

### 互联网信息服务算法推荐管理规定与算法备案系统
- URL / 标识：https://www.miit.gov.cn/jgsj/waj/wjfb/art/2022/art_a6ae77ea1f5e401eb8cc6819b869fdfa.html ; https://www.cac.gov.cn/2022-02/25/c_1647395666889023.htm
- 抓取 / 拉取日期：2026-05-24
- 用途：Task F 算法备案、安全评估触发条件参考
- 数据格式：HTML
- 许可状态：官方公开部门规章 / 通告
- 存储位置：`01_research/compliance/compliance_checklist.md`
- 责任人：Codex

### 互联网信息服务备案资料
- URL / 标识：https://www.gov.cn/zhengce/2022-08/23/content_5722707.htm ; https://hunca.miit.gov.cn/bsfw/bszn/art/2024/art_7ef0d8bd3b0d433ba4b9b277f883f74d.html
- 抓取 / 拉取日期：2026-05-24
- 用途：Task F ICP / 小程序备案与个人主体备案风险参考
- 数据格式：HTML
- 许可状态：官方公开法规 / 办事指南
- 存储位置：`01_research/compliance/compliance_checklist.md`
- 责任人：Codex

### 商标法与商标侵权判断标准
- URL / 标识：https://www.cnipa.gov.cn/art/2021/6/9/art_524_171344.html ; https://www.cnipa.gov.cn/art/2020/6/17/art_75_126939.html
- 抓取 / 拉取日期：2026-05-24
- 用途：Task F MARD / COCO 品牌名描述性使用边界
- 数据格式：HTML
- 许可状态：官方公开法律 / 规范性文件
- 存储位置：`01_research/compliance/compliance_checklist.md`
- 责任人：Codex

### 小红书蒲公英平台
- URL / 标识：https://pgy.xiaohongshu.com/
- 抓取 / 拉取日期：2026-05-24
- 用途：Task F 小红书商业合作官方路径参考
- 数据格式：HTML
- 许可状态：公开平台页面；规则细则需登录后台复核
- 存储位置：`01_research/compliance/compliance_checklist.md`
- 责任人：Codex

### P1 OpenAI-compatible image API run
- URL / 标识：OpenAI-compatible reverse proxy base URL from local `.env`
- 抓取 / 拉取日期：2026-05-24
- 用途：Task C P1 `gpt-image-2` 图像编辑 PoC，生成 AI 样本后接 Task B 量化流程
- 数据格式：API JSON / PNG
- 许可状态：用户提供的本地 API 配置；key 不入库
- 存储位置：`01_research/tech/poc_results.csv`, `01_research/tech/poc_samples/`
- 责任人：Codex

### 拼豆尺寸、色卡与图纸交付格式参考
- URL / 标识：https://www.hama.dk/en/hama-info/colour-chart/ ; https://www.hamabeadsusa.com/pages/hama-bead-sizes-and-categories ; https://perler.com/collections/pegboards ; https://perler.com/content/project_guides/perler-project-guide_color-wheel-and-shapes.pdf ; https://www.artkalfusebeads.com/pages/a-color-chart ; https://www.pixel-pattern.com/color-converter ; https://www.pixel-beads.com/zh/mard-bead-color-chart ; https://bitbead.pomodiary.com/
- 抓取 / 拉取日期：2026-05-24
- 用途：Task C 补充拼豆领域知识，约束 AI prompt、尺寸、色卡匹配、成品预览与图纸导出
- 数据格式：HTML / PDF
- 许可状态：官方公开页面 / 公开工具页面；MARD 非官方资料需后续用实物色卡复核
- 存储位置：`01_research/tech/perler_bead_domain_notes.md`, `01_research/tech/prompts.md`
- 责任人：Codex

### Hama official size / colour-code references
- URL / 标识：https://hama.dk/en/pages/the-foundation-stones-of-hama ; https://www.hama.dk/en/hama-info/colour-chart/
- 抓取 / 拉取日期：2026-05-24
- 用途：Task H 确认 Hama Mini 2.5mm、Midi 5mm、Maxi 10mm 规格，以及三种规格共用色号体系；为 `hama_*.json` 写入尺寸与来源说明
- 数据格式：HTML
- 许可状态：官方公开页面；HEX 未公开
- 存储位置：`01_research/colormap/build_full_bead_db.py`, `01_research/colormap/hama_*.json`, `01_research/colormap/README.md`
- 责任人：Codex

### Bitbead Hama / Perler / Artkal structured colour pages
- URL / 标识：https://bitbead.pomodiary.com/en/colors/hama ; https://bitbead.pomodiary.com/en/colors/perler ; https://bitbead.pomodiary.com/en/colors/artkal ; https://bitbead.pomodiary.com/en/colors/artkal-mini
- 抓取 / 拉取日期：2026-05-24
- 用途：Task H 提取 Hama、Perler、Artkal Mini 的公开结构化 code / name / HEX，用于生成品牌豆径 JSON 和跨品牌 CIEDE2000 对照
- 数据格式：HTML
- 许可状态：公开工具页面；商用复用许可未知；HEX 仅作近似参考
- 存储位置：`01_research/colormap/build_full_bead_db.py`, `01_research/colormap/hama_*.json`, `01_research/colormap/perler_5mm.json`, `01_research/colormap/artkal_2_6mm.json`
- 责任人：Codex

### Perler official product and colour references
- URL / 标识：https://perler.com/products/1-000-perler-beads-white ; https://perler.com/products/6-000-perler-beads-white ; https://perler.com/products/2-000-mini-perler-beads-black ; https://perler.com/products/biggie-beads-bucket ; https://perler.com/content/downloads/perler-bead-color-reference-jan2020.pdf
- 抓取 / 拉取日期：2026-05-24
- 用途：Task H 确认 Perler classic 5mm、Mini、Biggie 产品规格、SKU、价格样本与官方色卡 PDF 存在性；HEX 仍由第三方工具页补
- 数据格式：HTML / PDF
- 许可状态：官方公开页面；商用复用许可未知
- 存储位置：`01_research/colormap/build_full_bead_db.py`, `01_research/colormap/perler_5mm.json`, `01_research/colormap/README.md`
- 责任人：Codex

### Artkal official series and size references
- URL / 标识：https://www.artkalfusebeads.com/blogs/faq/artkal-beads-size ; https://www.artkalfusebeads.com/collections/mini-c-2-6mm-artkal-beads/artkal-beads ; https://www.artkalfusebeads.com/blogs/artkal-color-chart/artkal-color-chart ; https://www.artkalfusebeads.com/pages/a-color-chart ; https://www.artkalfusebeads.com/pages/r-color-chart ; https://www.artkalbead.com/uploads/10mm-X-bead-color-chart-15-Colors.pdf
- 抓取 / 拉取日期：2026-05-24
- 用途：Task H 确认 Artkal C/A/M 2.6mm、S/R 5mm、X 10mm 系列与官方色数口径；结构化 HEX 由 Pixel Pattern / Bitbead 补
- 数据格式：HTML / PDF
- 许可状态：官方公开页面；商用复用许可未知
- 存储位置：`01_research/colormap/build_full_bead_db.py`, `01_research/colormap/artkal_*.json`, `01_research/colormap/README.md`
- 责任人：Codex

### Pixel Pattern Color Converter structured tables
- URL / 标识：https://www.pixel-pattern.com/color-converter
- 抓取 / 拉取日期：2026-05-24
- 用途：Task H 结构化提取 MARD 英文名、Artkal S 系列、Perler / Hama 交叉参考；生成 palette JSON 与同豆径 CIEDE2000 对照
- 数据格式：HTML table
- 许可状态：公开工具页面；页面说明部分数据来自官方 PDF/OCR与社区参考，商用复用许可未知
- 存储位置：`01_research/colormap/build_full_bead_db.py`, `01_research/colormap/mard_5mm.json`, `01_research/colormap/artkal_5mm.json`
- 责任人：Codex

### MARD / COCO / other domestic public bead references
- URL / 标识：https://www.pindou.online/colors ; https://artkalbeads.com/artkal_beads/527.html ; https://apps.apple.com/nz/app/%E6%8B%BC%E8%B1%86%E5%A4%A7%E5%B8%88/id6760127746 ; https://git.xiongxiao.me/abearxiong/get-colors-from-beans
- 抓取 / 拉取日期：2026-05-24
- 用途：Task H 记录 MARD 291/221、COCO 291/221、黄豆豆、咪小窝、盼盼等国产公开色卡，以及 MARD 2.6mm 221 色商品存在性
- 数据格式：HTML / App Store 页面 / JSON
- 许可状态：公开页面；get-colors-from-beans 为 MIT；其他页面商用复用许可未知
- 存储位置：`01_research/colormap/_source_get-colors.json`, `01_research/colormap/build_full_bead_db.py`, `01_research/colormap/*_5mm.json`, `01_research/colormap/*_2_6mm.json`
- 责任人：Codex

---

## 类别建议（Codex 调研时分类）
- 色卡数据：MARD 官方、COCO 官方、电商列表
- 算法参考：GitHub 仓库、ECCV/CVPR 论文、博客教程
- 竞品数据：小程序竞品、Web 端工具、小红书账号
- 合规材料：法律条文、备案指南、平台规则
- AI 模型：HuggingFace、ModelScope、CivitAI
