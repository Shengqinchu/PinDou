# VISION3：手写标题、主域名与店主编辑

视觉与内容来源：店主的 vision3.pdf（7 页）及首页图 ZIP（12 张）。逐项清单在 `02_product/STUDIO_VISION3_PROGRESS.md`。本文件覆盖旧版冲突要求。

## 字体与素材

- 英文保持 DM Serif Display / Outfit；中文正文保持 PinDou Sans SC。中文 h1–h6 使用圆润手写的 **Xiaolai / 小赖字体 v3.126**。实际比较了小赖与 LXGW Marker Gothic，前者的圆头、自然的横画和字面更接近店主 logo。中文标题中的拉丁字母仍优先使用 Outfit。
- 字体来源：[作者项目](https://github.com/lxgw/kose-font)、[固定发行版](https://github.com/lxgw/kose-font/releases/tag/v3.126)。使用 OFL 1.1，原许可保留在 `public/studio-fonts/OFL.txt`。完整 TTF 不发送给顾客；当前标题核心为 414 字形 / 69,556 bytes，其他汉字分片通过 unicode-range 按需加载。字体源/各片校验值记在 manifest；新增后台标题可用其他分片，无需重新部署。
- 页头完整中/英品牌图、独立小狗来自 PDF 嵌入原图。首页大图使用 PDF 指定插画。首页预告使用 ZIP 的第 12 张四宫格作品，空间相册使用全部 12 张照片。
- 原始素材保留在本地 `artifacts/vision3/originals/`，源文件哈希记录到执行表与 `public/studio-media/v3/sources.json`。交付 WebP 为等比例缩放，未重画、调色或裁切。日记保留带水印的原始图片字节。
- 白底、黑灰字；首页两个入口白色。其余原紫色选择/操作/阴影衬色统一浅蓝。维持 300ms 可中断按压及卡片反馈、原生滚动、系统/本站动效偏好。

## 实际采用的技能

1. 项目 `pindou-studio-design`：源素材、文案授权、共享动效、微信/原生偏好、旧工具保护。
2. `pdf`：7 页全部渲染并视觉审阅；原嵌入图与截图位置逐一对应。
3. [Impeccable typeset](https://github.com/pbakaus/impeccable/blob/main/skill/reference/typeset.md)：分别检查角色、字号、密度、中文/英文、窄屏、字体交付；先做真实文案字体比较再选型。
4. [Impeccable operate](https://github.com/pbakaus/impeccable/blob/main/skill/reference/operate.md)：后台以明确的草稿、发布、状态、恢复路径和熟悉表单为主。已有品牌的标题规则优先于其“一套无衬线”的一般建议。
5. `apisell-knowledge`：核实 PinDou 原站、Cloudflare 入口与源站；只使用已有同项目翻译接入，不输出凭证。

Impeccable 当前本地研究包没有 launcher，已明确说明 context / detector 未运行；使用文档规定的 fallback。字体、样式和运行时检查由实际代码与浏览器完成，不宣称安装完整上游插件，也没有将现成图重画成另一个 logo。

## 编辑与发布

网站编辑按页面/功能列出已批准的双语内容，可查找文字、保存草稿、使用真实手机/电脑宽度预览、发布并载入历史版本。媒体使用稳定逻辑名称，上传后保留比例。网站优化图片、日记原图与发布内容存于 Studio shared 目录及独立 SQLite，常规代码部署不会覆盖。

页面模块懒加载时才注册内容代理；不会为了编辑能力把全部日记或后台模块塞入首页。公开接口仅返回已发布覆盖，草稿受现有管理员认证保护。动态占位符、图片路径、日期及发布版本在服务端校验。文字始终作为文本渲染。

小红书导入只接受平台分享页和官方图片域名，验证作者为小狗双吉，读取全部照片后才建立草稿。失败/重复/不完整有明确提示。英文翻译保留原文，店主可以编辑后发布；日期晚于 2026-06-24 的已发布完整日记按原帖日期排序，最新一篇自动置顶。导入不会绕过登录或验证码。

## 域名与加载决策

品牌主页使用 `https://pindoupuppy.com/`；www 也到同一主页。主要路径为 `/visit`、`/details`、`/journal`、`/shop`、`/manage`。旧 `/studio/*` 页面永久跳转到对应短路径；旧工具 `/upload`、`/tutorial`、API 和静态资源继续由旧站提供。

本阶段预约/账户/支付不拆子域名。拆分域名不会自动减少脚本量，还会引入跨源连接、登录状态和资源复用的额外设计；是否拆分应由独立应用/部署/安全边界决定。目前一个品牌网站用路径更易维护。

- [Vue Router 路由懒加载](https://router.vuejs.org/guide/advanced/lazy-loading.html)：访问时只加载对应页面；后台不随首页下载。
- [web.dev 关键资源预加载](https://web.dev/articles/preload-critical-assets)：首页插画仅在首页预加载，核心中文字片仅对中文偏好预加载；首图高优先级、srcset 按宽度选择。
- [web.dev 预取策略](https://web.dev/learn/performance/prefetching-prerendering-precaching)：悬停/键盘聚焦后预取公共页面；首页空闲时最多预取预约页。Save-Data/2G 下关闭预取，不预取个人预约、订单或管理员页面。
- 轮播仅挂载当前与相邻照片，其他图片延迟请求。哈希脚本/字体使用长期缓存；HTML、版本、预约和编辑状态保持新鲜。
- 保留浏览器原生缩放、VisualViewport、安全区与微信适配；微信 UA / WebKit 模拟与真机验收明确分开。

迁移保留旧会话：www 的公共品牌页面统一到主域名；旧生成器、API、管理员及预约/订单回执不强制跨域重定向，避免丢失既有同源令牌或预约 Cookie。

首个 HTML 由 Studio 服务在已校验的构建文件中嵌入已发布覆盖值（惰性 JSON，转义 `<`），Vue 首次渲染直接读取，避免已编辑标题在加载时切换。首页预加载同时读取店主当前封面；草稿不进入公开 HTML。静态字体/图片/脚本继续交给 Nginx。
