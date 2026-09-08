# PinDou Studio 当前设计规范

2026-09-08，VISION2。逐项需求和店主澄清见 `02_product/STUDIO_VISION2_PROGRESS.md`。本文件替代上一版蓝灰底/衬线中文的视觉规则；历史方向可在 Git be46a3d 查看。

## 设计判断

这是 Hamilton 家庭手作店的品牌网站。白底实拍、店主手写 logo、黑灰字体和零星浅彩，让页面像这家小店本身。中文标题与正文共用清楚的无衬线体系；英文保留原来认可的 DM Serif Display + Outfit。预约/后台以操作清楚为优先，日记以原帖图文为主。

## 真实来源与具体应用

| 来源 | 采用的规则 | 当前落点 |
|---|---|---|
| [ROOMCO](https://roomco.ca/) | 白色大背景、照片主导、浅色仅作局部衬底 | 首页、照片轮播、日记、详情 |
| [Pentagram / HIUT](https://www.pentagram.com/work/hiut) | 功能性正文字体与店家自己的手写品牌字形成层次，品牌源自真实制作者 | 中文统一无衬线；PDF中手写logo用于BrandMark |
| [Taste](https://github.com/Leonxlnx/taste-skill) | 先审既有品牌/内容，避免把“高级”等同衬线字、通用色块和到处动的装饰；交互状态要成套 | typography.css / interactions.css / plan-price-reveal |
| [Impeccable](https://github.com/pbakaus/impeccable) | 字体/配色/交互/响应式分别审；简化文字层级，克制装饰，保留业务事实；批量检查桌面与手机 | 分层字体、浅色token、分页日历、设置抽屉与验证记录 |
| [GSAP](https://gsap.com/docs/v3/GSAP/gsap.context()/) / 本地 hyperframes:gsap skill | 作用域、matchMedia清理、连续时间线、统一状态曲线、reduced motion | 首页标题/品牌元素/照片顺序；AutoHeight；既有可逆弹层 |
| 当前 Turnitin_generation 的 FRONTEND_INTERACTION_AND_MOTION_STANDARD.md | 300ms ease-in-out 同步父子反馈、真实按下/松开、小幅位移、细指针限定hover | 共享按钮、套餐标签、价格展开和后台控件 |
| [photo-abstract-editorial](https://github.com/ZzzLc0405/photo-abstract-editorial) | 先观察实拍的明暗/间距/配色，保留照片内容 | 实拍不重绘；它的“生成英文标题双联海报”步骤不适用本网站且会冲突店主文案锁，因此没有伪称执行该海报流程 |

技能使用说明：Taste、Impeccable 的上游说明保存在开发研究资料；本次实际采用以上步骤，不宣称安装过完整插件。Impeccable launcher 未包含在本地参考包，已向店主说明，按其 fallback 手动使用文档。GSAP 库实际在运行代码中使用。高德地图面向中国场景，本店加拿大地址继续使用 Google Maps 普通链接。没有为“使用技能”而给实拍套滤镜或生成另一间工作室。

## 品牌与色彩

- PDF 第4–7页四张品牌图片原样提取；`public/studio-brand/` 保留原始字节。`BrandMark.vue` 和 `BrandMotif.vue` 使用 CSS 视窗呈现字标/小狗/星/爱心/骨头，不重写手绘文字，不假称 AI 生成。
- Header 以手绘字标和小狗构成标识；footer呈现完整简版；首页仅有少量来源明确的元素，形成一次性的入场层次。纯内容卡片不伪装按钮。
- 主背景 #ffffff；主文字 #292a2b；次文字 #626366；线条 #e1e2e4。
- 操作衬色 #e7e4f4；次级衬底 #f3f4f6；储值信息淡绿 #f4f6f2；开学信息淡杏 #faf4f0。按钮和标签的文字保持黑灰。颜色少量出现，不再整页蓝灰。
- 拟物阴影仅提示可交互；主要轮廓圆润，照片保留真实比例关系。按钮使用胶囊边界，信息容器使用12–16px圆角。

## 字体与文字

- 中文：自托管 Noto Sans SC 子集（PinDou Sans SC），fallback PingFang SC / Microsoft YaHei。标题约28–64px、weight500；正文14–16px；输入至少16px。取消中文衬线标题。
- 艺术字来自店主手绘logo，避免给表单、细则和长文另配艺术字体。
- 英文：DM Serif Display 标题 / Outfit 正文延续既有认可。用户日记原文用中文 sans 渲染，即使界面切为英文也不擅自翻译。
- 原始字体来源与OFL许可保留；子集脚本同时读取内容JSON，防止集中化后漏掉汉字。
- 用户指定换行以内容中的 `\n` 保存。手机允许同一段自然折行，不通过删字适配。
- 文案唯一来源、变更授权和锁定检查见 `02_product/copy/STUDIO_COPY_RULES.md`。设计工作不授权改文案。

## 动效实现

- 按钮、标签背景、图标和按压统一300ms cubic-bezier(.42,0,.58,1)，同一状态一起启动和结束。触屏不残留hover，抬手不额外延迟。
- 套餐选前不显示价格；选后由AutoHeight从当前高度连续展开。改变视口时直接重排，避免横屏/键盘下错误插值。动画不伪造金额、付款或占位状态。
- 首页内容先出现，随后小狗/星/心和照片完成一次入场。GSAP matchMedia作用域在离开页面后清理；缩减动态模式直接呈现完整静态状态。
- 保留0830修正过的可逆照片过渡、独立scrim/panel、原生dialog焦点与滚动恢复。不退回全局飞入、无意义无限循环或滚动劫持。
- 后台设置抽屉使用相同原生dialog组件，出错保留输入，版本冲突由服务器识别；保存后读真实配置。

## 页面与可访问性

- 日历：宽屏7列，中屏4列，窄屏3列；翻页覆盖完整14天。只有纵向滚动；同一个格子至少44px高，键盘导航根据当前列数计算。图例、日期切换、说明、表格顺序一致。
- 客户与后台中文/英文、窄屏/平板/桌面/横屏分别验证。菜单关闭、焦点、价格中间态、图片与字体实际渲染需要检查。
- 微信采用VisualViewport、安全区、原生输入和页面返回刷新。UA/引擎模拟不能冒称真机验收。
- 日记有独立文章页。当前9篇完整原帖（包含店主新补8篇/80图）与10篇明确标识的合集摘录。图片可点击放大。整个34篇合集的完整图文尚未全部取得，继续作为未完成内容项。
