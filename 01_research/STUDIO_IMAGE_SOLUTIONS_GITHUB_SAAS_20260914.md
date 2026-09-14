# 小店图片加速：GitHub 与商业平台选型

后续采用现有 Pillow 与 CDN 缓存完成部署，结果见 [图片与动效验收](../07_ops/STUDIO_IMAGE_MOTION_VERIFICATION_20260914.md)。下文保留选型时的调研结论。

核验日期：2026-09-14。对象是现有 Vue 3 / Vite + FastAPI 小店、Cloudflare 代理与内容哈希图片，不是新建商城。顾客以加拿大为主；本轮未做加拿大不同运营商及中国大陆的多地测速。

## 判断与建议

上一轮证明了缩略图和提前加载有用，但没有证明那是最佳实现。此次比较后，**优先验证 Cloudflare Images 的外部原图转换，再配合前端按需加载；不想依赖新的托管功能时，复用现有 Pillow 生成静态缩略图是低成本备选。** 这是按接入量、维护量、费用与现有系统匹配得出的选择，不是多个 SaaS 在相同网络条件下的速度排名。

成熟服务主要负责缩图、格式转换与分发缓存；页面仍需决定取哪种尺寸、先加载哪些图片。我们用按钮切换 A/B 系列，不能把“网页导航预取”工具直接当成商品图片预加载。原图、现有商品资料与后台编辑流程都应保留。

最值得进入实际验收的四条路线：

| 路线 | 适用判断 | 实施量与主要代价 |
|---|---|---|
| Cloudflare 外部原图转换 + 前端选择尺寸 | **托管首选候选**；已有 Cloudflare，同域接入可保留上传与原图地址 | 需启用域名转换能力、接入图片 URL/尺寸选择并测试；账号可用性尚未确认 |
| Pillow 静态缩略图 + 当前 Cloudflare | **现有系统的低成本备选**；不增加独立图片服务器 | 在现有上传处理和一次性补图任务中生成少量固定尺寸；自己维护派生图与失败重试 |
| ImageKit 外部源站 | **独立 SaaS 备选**；可保留源站文件 | 增加供应商账号/图片域名与配额管理，免费流量用尽会停供 |
| imgproxy / Imagor + CDN | 图片规模显著增长、需要复杂实时变换时再选 | 增加进程/容器、缓存、升级与监控；目前几百张封面不必先引入该运维量 |

## 检索范围与证据边界

- 按 `GitHub Research` 技能，执行 5 组 GitHub 仓库搜索，返回 79 条、去重 74 个仓库；结合官方项目与框架适配继续筛选，共核对 **17 个开源项目**。这不是 GitHub 全站穷尽检索。
- 对下表逐项读取 GitHub API 元数据、README、最新 release 信息；Stars、最近推送和许可证均为本次快照。最近推送不等于最近稳定版，README 主分支也可能是测试版。
- 核对 **8 个商业图片平台**的当前官网定价/文档，另核对 Cloudflare Polish、Speed Brain 和已下线的 Mirage，避免采用过时的一键加速建议。
- 没有新注册账号、开通付费套餐、调整生产配置或发布商品图片。没有把供应商自测成绩当成我们的实测。

## GitHub 项目筛选

| 项目 | 技术/用途 | Stars | 许可证 | 最近推送 / Release | 我们的取舍 |
|---|---|---:|---|---|---|
| [lovell/sharp](https://github.com/lovell/sharp) | JavaScript；Node 图像处理库 | 32,677 | Apache-2.0 | 2026-09-13 / v0.35.4 | 静态派生图首选之一；已有本地体积测试 |
| [libvips/pyvips](https://github.com/libvips/pyvips) | Python；Python libvips 绑定 | 814 | MIT | 2026-08-30 / 未列 GitHub release | 大批量时再评估；当前可先复用 Pillow |
| [python-pillow/Pillow](https://github.com/python-pillow/Pillow) | Python；Python 图像处理 | 13,812 | MIT-CMU（已读 LICENSE） | 2026-09-14 / 12.3.0 | 现有后端已使用，接入新增量最小 |
| [imgproxy/imgproxy](https://github.com/imgproxy/imgproxy) | Go；Go 实时图片代理 | 11,066 | Apache-2.0 | 2026-09-14 / v4.0.14 | 成熟备选；需要独立服务/CDN缓存 |
| [cshum/imagor](https://github.com/cshum/imagor) | Go；Go 实时处理与存储 | 4,022 | Apache-2.0 | 2026-09-14 / v1.9.6 | 成熟备选；适合较复杂图片链路 |
| [thumbor/thumbor](https://github.com/thumbor/thumbor) | Python；Python 图片服务器 | 10,518 | MIT | 2026-09-08 / 7.8.0 | 仍有维护；当前没有 Thumbor 生态依赖 |
| [h2non/imaginary](https://github.com/h2non/imaginary) | Go；Go/libvips 服务 | 6,075 | MIT | 2025-11-08 / v1.2.4 | 最新正式 release 仍为 2020，降低优先级 |
| [unjs/ipx](https://github.com/unjs/ipx) | TypeScript；TypeScript/Sharp 图片服务 | 2,453 | MIT | 2026-09-13 / v4.0.0-beta.1 | v4 当前是 beta；不把主分支当稳定版 |
| [nuxt/image](https://github.com/nuxt/image) | TypeScript；Nuxt 图片组件/多 provider | 1,547 | MIT | 2026-09-14 / v2.1.0 | 现有 Vue/Vite 不是 Nuxt，不为此迁移框架 |
| [aFarkas/lazysizes](https://github.com/aFarkas/lazysizes) | JavaScript；浏览器延迟加载 | 17,716 | MIT | 2024-04-03 / 5.3.1 | 功能可参考；维护/发布节奏较旧 |
| [verlok/vanilla-lazyload](https://github.com/verlok/vanilla-lazyload) | JavaScript；浏览器图片可见区控制 | 7,854 | MIT | 2026-09-11 / 19.1.3 | 轻量可用，但不提供服务端缩图 |
| [GoogleChromeLabs/quicklink](https://github.com/GoogleChromeLabs/quicklink) | JavaScript；链接预取/预渲染 | 11,290 | Apache-2.0 | 2026-09-01 / 3.0.2 | 分类按钮需要手动适配，不是即插即用 |
| [GoogleChrome/workbox](https://github.com/GoogleChrome/workbox) | JavaScript；Service Worker/PWA 缓存 | 13,014 | MIT | 2026-09-02 / v7.4.1 | 现有图片HTTP缓存有效，暂不新增离线层 |
| [GoogleChromeLabs/squoosh](https://github.com/GoogleChromeLabs/squoosh) | TypeScript；浏览器图像压缩应用 | 25,881 | Apache-2.0 | 2026-09-14 / 未列 GitHub release | 适合人工比较画质，不是生产图片CDN |
| [vueuse/vueuse](https://github.com/vueuse/vueuse) | TypeScript；Vue 3 可组合工具 | 22,354 | MIT | 2026-09-10 / v14.4.0 | 前端可见区/预读辅助优先候选 |
| [alexjoverm/v-lazy-image](https://github.com/alexjoverm/v-lazy-image) | JavaScript；Vue 延迟/渐进图片组件 | 987 | MIT | 2024-07-17 / 未列 GitHub release | 可参考；最近推送为 2024，优先级次于 VueUse |
| [aws-solutions/dynamic-image-transformation-for-amazon-cloudfront](https://github.com/aws-solutions/dynamic-image-transformation-for-amazon-cloudfront) | TypeScript；AWS 官方动态图片架构 | 1,469 | Apache-2.0 | 2026-09-10 / v8.1.1 | 完整但引入AWS服务较多，不符合当前轻量需求 |

Pillow 的 GitHub 元数据将许可证标为 `NOASSERTION`，实际读取仓库 LICENSE 后确认其文本写明 MIT-CMU；pyvips 的 MIT 指 Python 包，部署还需考虑其 libvips 依赖。这里记录许可证，不替代完整的分发许可审查。

### 对我们有用的开源组合

- **图片处理**：现有服务已经导入 Pillow，几百张图片只生成三档尺寸，优先复用即可。Sharp 适合 Node 上传/后台任务；其底层使用 libvips，且上一轮已用它对真实 B 系列做体积实验。pyvips 可供将来 Python 大批量处理使用。[Pillow](https://github.com/python-pillow/Pillow)、[Sharp](https://github.com/lovell/sharp)、[pyvips](https://github.com/libvips/pyvips)
- **Vue 可见范围控制**：VueUse 的 `useIntersectionObserver` 和 `useImage` 可辅助实现可见图片加载、后台预读。它们本身不提供图片压缩或 CDN；应按需引入，或沿用浏览器原生 API。[观察可见范围](https://vueuse.org/core/useintersectionobserver/)、[预载图片](https://vueuse.org/core/useimage/)
- **独立图片代理**：imgproxy 和 Imagor 均在持续发布。没有采用旧讨论中“Thumbor 仍停在 Python 2”的说法，因为本次实际看到 Thumbor 7.8.0 和近期维护。对于我们的规模，额外服务的维护成本比算法选择更值得关注。[imgproxy](https://github.com/imgproxy/imgproxy)、[Imagor](https://github.com/cshum/imagor)、[Thumbor](https://github.com/thumbor/thumbor)
- **不是直接替换件**：Nuxt Image 是 Nuxt 模块，现有站是普通 Vue/Vite；可以借鉴 provider 与响应式图片方案，不需要为图片优化迁移整个网站。Quicklink 默认处理链接预取，商品分类按钮需要额外接入。Workbox 更适合有明确离线/PWA需求的场景，当前 HTTP 图片缓存已工作，不宜为这一个问题再增加一套 Service Worker 缓存生命周期。[Nuxt Image](https://github.com/nuxt/image)、[Quicklink](https://github.com/GoogleChromeLabs/quicklink)、[Workbox](https://github.com/GoogleChrome/workbox)

## 商业平台比较

以下为官网当前基础标价，美元口径；“免费”均有范围或配额，不代表所有功能无限使用。未购买套餐，账单仍应以账号结算页面为准。

| 平台 | 当前费用/限制 | 与现有网站的匹配 | 本次取舍与官方依据 |
|---|---|---|---|
| Cloudflare Images：外部源图转换 | 免费每月 5,000 个唯一变换；Paid 超出后 $0.50 / 1,000 个 | 原图留在现有 HTTPS 源站，同域转换与边缘缓存 | **首选验证**。免费超额后已缓存版本可继续，新变换可能报 9422，应保留原图回退。[定价](https://developers.cloudflare.com/images/pricing/)、[远程图片流程](https://developers.cloudflare.com/images/optimization/transformations/overview/) |
| ImageKit | 免费 20 GB/月流量、3 GB DAM；Lite $9/月含 40 GB，超出 $0.50/GB | 可用 Web Folder/Web Proxy 接现有服务器，无须先迁移所有原图 | **托管备选**。免费流量到顶停止交付；自定义域名、AVIF 等不要默认计入免费权益。[价格](https://imagekit.io/plans/)、[外部源站](https://imagekit.io/docs/integration/web-server) |
| Bunny Optimizer | $9.50/每个 Pull Zone/月，另加 CDN 流量；北美 Standard $0.01/GB | 支持实时尺寸转换，需要另建图片分发接入 | 用量增长后费用直观，目前可先验证免费候选。[Optimizer](https://bunny.net/pricing/optimizer/)、[CDN](https://bunny.net/pricing/cdn/)、[计费 FAQ](https://bunny.net/faq/) |
| Cloudinary | 免费 25 credits；Plus 月付 $99，年付折算 $89/月；credits 合并计算变换、存储与流量 | 支持 remote fetch、自动格式、媒体管理 | 功能成熟且完整，现阶段媒体管理价值有限；免费额度可试用，但付费档较高。[价格](https://cloudinary.com/pricing)、[credits 规则](https://cloudinary.com/documentation/billing_and_plans) |
| imgix | 30 天/100 credits 试用；Starter $25/月或 $250/年，100 credits/月 | 适合现有源站的图片 API 与 CDN | 能胜任，但当前起价与重新接入的收益不如前两项明确；100 credits 是共享资源预算，不能把所有“最高用量”当可同时免费用满。[价格](https://www.imgix.com/pricing) |
| Uploadcare | 免费页明确 Personal use only；Pro 年付展示价 $66/月，官方比较页列月付 $79 | 上传、媒体处理和交付较完整 | 商业小店不按个人免费层预算；付费成本偏高。[价格](https://uploadcare.com/pricing/)、[官方月付对照](https://uploadcare.com/compare/filestack-alternative/) |
| Sirv | 免费 500 MB 存储、2 GB/月交付；Business $19/月起，基础页列 20 GB 流量 | 适合商品缩放、360° 展示及动态图片 | 我们不需要其主要展示功能，免费流量也较小。免费 branding 具体涉及 spins/zooms，不能误说所有静态商品图都有水印。[价格](https://sirv.com/pricing/) |
| ImageEngine | 官方正转向自托管 Kube 和非商业 Sandbox；当前主页面为企业规模估算/联系销售 | 更适合自有云基础设施、较大流量企业 | **排除当前范围**，不采用搜索结果中的旧 SaaS $49/$99 价格。[当前产品/价格](https://imageengine.io/pricing/)、[迁移说明](https://support.imageengine.io/hc/en-us/articles/360059637451-Frequently-Asked-Questions) |

Cloudflare 存储型 Images 与外部源图转换是两种计费路径：这里推荐保留原图的外部转换，并未建议迁移到付费托管图片桶。Cloudinary 的 credits 也不能理解为每种资源各送 25 份；它们会相加，典型图片规则为 1 credit 对应 1,000 次变换或 1 GB 存储或 1 GB 交付。[Cloudflare 路径](https://developers.cloudflare.com/images/)、[Cloudinary 资源规则](https://cloudinary.com/documentation/developer_onboarding_faq_credits)

## 以当前小店规模计算

上一轮实测 240 张独立封面约 20.3 MB。若仅为这些封面提供固定 320/480/640 三档转换，组合数为 **240 × 3 = 720**，约占 Cloudflare 免费额度 14.4%。此为本小店新增用量估算；账号其他图片、视频或新增尺寸需要合并计数，不是永久免费承诺。

Cloudflare 同月同一源图/参数的重复访问只算一次变换；`format=auto` 因浏览器返回 AVIF/WebP 不会额外拆成两个计费组合。固定尺寸有助于避免无意义的变换增多。[计费定义](https://developers.cloudflare.com/images/pricing/)

下面只是流量敏感性估算：每次未命中浏览器缓存的访问下载 24 张图，平均体积取上一轮 B 系列 480 px 实验的 38,117 字节；不代表真实月访问量。保留现有原图存储，未计税费、其他媒体和现有服务器费用。

| 假设月访问数 | 图片交付量 | Cloudflare 新增转换费 | ImageKit | Bunny Optimizer + 北美 Standard CDN |
|---:|---:|---:|---:|---:|
| 1,000 | 0.915 GB | $0 | $0 | $9.51 |
| 10,000 | 9.148 GB | $0 | $0 | $9.59 |
| 50,000 | 45.741 GB | $0 | $11.87（Lite） | $9.96 |

表内 Cloudflare 以账号额度足够且仍只有 720 个变换为条件；ImageKit 以 Free/Lite 和上述官网流量规则计算；Bunny 以单一 Pull Zone 和北美流量计算。不是各家实际速度对比，也不是完整托管迁移报价。计算脚本和输入位于 `artifacts/image-solutions-20260914/cost-scenarios.json`。

## 当前接入状态实测

使用干净 Chromium 会话访问本网站公开图片：

- B1 原图：HTTP 200，85,836 字节，解码为 800 × 800，长期 immutable 缓存有效。
- 按官方 URL 结构请求 `width=480,quality=85,format=webp`：HTTP **404**，不是一张已经成功转换的图片。因此不能把“Cloudflare 有免费能力”说成“我们的站已经启用”。下一步需核对域名 Images/Transformations 配置及当前账号可用额度。[官方 URL 结构](https://developers.cloudflare.com/images/optimization/features/)
- 原图的响应 Content-Type 为 `application/octet-stream`，浏览器仍能解码。接入时应将媒体 MIME 正确性作为兼容性检查；没有证据证明它导致了本次 404 或原来的慢加载。
- 未在其他平台新建账号或上传测试图，尚未完成这些服务对相同商品图的公平 A/B 测速，因此不宣称 Cloudflare 的转换速度已胜过 ImageKit/Bunny。

## 常见“一键加速”为什么不直接解决这张截图

Cloudflare **Polish** 可压缩现有图，但不会替页面选择缩小后的实际尺寸，且要求 Pro 或以上；我们多数色号图本身已是 WebP，不能仅凭宣传判断再压缩收益。**Mirage 已于 2025-09-15 下线**，旧教程不可继续作为实施方案。[Polish](https://developers.cloudflare.com/images/polish/)、[Mirage 状态](https://developers.cloudflare.com/speed/optimization/images/mirage/)

**Speed Brain** 面向后续网页导航，要求支持的 Chromium 与可缓存页面；我们商品分类是同页 Vue 按钮，且 HTML/业务接口有各自缓存边界，所以不能指望开启它自动预读 B 系列图片。Quicklink 的默认监听对象同样是链接，若用它仍需自行接入图片 URL 与分类意图。[Speed Brain](https://developers.cloudflare.com/speed/optimization/content/speed-brain/)、[Quicklink](https://github.com/GoogleChromeLabs/quicklink)

NitroPack 这类整页优化产品另有缓存、脚本和图片优化功能，但它们的功能宣传不是与当前 Vue/FastAPI 应用兼容的证明。本轮不把整页优化/替换平台作为解决商品分类图片的首选。[NitroPack 图片优化说明](https://support.nitropack.io/en/articles/8390289-image-optimization)

## 下一步具体怎么验证

1. 先确认现有 Cloudflare 域名能启用外部原图转换。用 B1、B32、一个全系列合图、一张风景原图验证三档尺寸、格式与完整构图；原图及数据库关联不改。
2. 列表按 `srcset` / `sizes` 选择预览尺寸。当前首屏优先；其余仅在接近可见区时请求。详情继续提供原图。
3. 使用现有 Vue 组件配合原生 API 或 VueUse，空闲/分类意图出现时低优先级预读下一组 4–8 张；最多并发 2 张，慢网/省流模式限制预读。
4. 测冷缓存、暖缓存、立即切分类、停留后再切、手机高密度屏幕、后台换图、图片服务失败回退。保留之前的 8 Mbps 模拟条件，至少重复多次再评价时延；有条件时加加拿大实际手机网络。
5. 若 Cloudflare 配置或实测未达预期，使用现有 Pillow 生成同样的三档静态派生图；需要更复杂实时裁剪时才引入 imgproxy/Imagor。ImageKit 可作为独立托管备选。

## 留档

所有检索与核验文件在 `artifacts/image-solutions-20260914/`：

- `github-searches.json`：5 组查询、79 条搜索结果。
- `github-repositories.json` 与 17 份 README：项目维护、许可证和版本快照。
- `Pillow-LICENSE.txt`：实际许可证文本核对。
- `cloudflare-probe.json`：原图解码与当前转换入口的 HTTP 结果。
- `cost-scenarios.json` / `estimate-costs.py`：假设流量与可复算费用。

上一轮原始测试与体积实验仍保留在 [图片加载评估](STUDIO_SHOP_IMAGE_PERFORMANCE_20260914.md)。本轮为研究与只读验证，线上未修改。
