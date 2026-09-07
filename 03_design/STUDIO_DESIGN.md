# 小狗拼豆铺 · 视觉与交互方向

设计判断：面向 Hamilton 手作爱好者的精品生活方式工作室，采用真实摄影主导的编辑式布局，兼顾轻松、亲切和留白。

## 核心决策

- 照片承担品牌表达：自然光、白桌、木地板、毛毡色块和细小的彩色豆子。使用店主公开照片，不用假工作室或通用图库替代。
- 奶油白底、深橄榄文字、砖红操作色，蓝灰只用于实景引出的局部大色面。彩色拼豆保留在照片里。
- 主视觉为文字与大幅实景的非对称并列，后续按空间、作品、体验、选购、到访的节奏展开。
- 英文展示字体 DM Serif Display，与 Outfit 正文搭配。中文标题采用 Noto Serif SC，中文正文和操作区采用 Noto Sans SC；以 PinDou Serif SC / PinDou Sans SC 的项目子集名称随站点发布。正文不再依赖设备上的微软雅黑。字体本地打包，不依赖访客连接外部字体 CDN。
- 商城只使用商品 / 材料实拍；展示作品不自动意味着该版权图案作为商品出售。成品类以定制询单处理。
- GSAP 负责首屏展开和轻微照片位移；控件沿用 T-Check 已验收的 `300ms ease-in-out` 节奏，提供同步的悬停、按压、恢复和焦点反馈。保持原生滚动，减少动态效果时父级和子图标统一取消位移。
- CTA 清楚区分“预约到店”“提交预约意向”“加入选购清单”“提交自提询单”。提交后显示真实编号和待确认状态。
- 联系方式不在浏览器长期存储；语言和不含个人信息的购物清单可以记忆。请求与后台数据使用 no-store。

## 参考来源与取舍

| 来源 | 本项目采用 | 不直接移植 |
| --- | --- | --- |
| [ROOMCO](https://roomco.ca/) | 实物摄影、留白、简短导航、购物入口 | 家居品类、促销弹窗、原站照片和标志 |
| [Apple AirPods](https://www.apple.com/airpods/) | 内容分段、清楚的动作层级、克制过渡 | 巨型视频、滚动劫持、苹果商标 |
| [Airbnb Experiences](https://www.airbnb.com/experiences) | 日期 / 人数的任务顺序、确认前看清信息 | 未接入排班时的虚假可订日历 |
| [Stripe Checkout](https://stripe.com/payments/checkout) | 输入、校验、摘要、完成状态的清晰顺序 | 未开通支付账户时的模拟付款 |

## Skills 调研

核查日期：2026-09-07。以下是上游来源和本轮取舍，项目 skill 为自主整理的窄范围适配，不宣称上游插件已全部安装。

| Skill | 上游 | 结论 |
| --- | --- | --- |
| photo-abstract-editorial | [作者仓库](https://github.com/ZzzLc0405/photo-abstract-editorial) | 已阅读入口。用于照片与抽象面板组合，不是整站生成器。本轮借鉴照片关系提取，保留原图；未来生成海报时单独调用 imagegen。 |
| Taste Skill | [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) | 已阅读方向推导、字体、配色和现有栈适配部分。用于页面设计判断；保留 Vue，不为 skill 偏好的 React 重建旧工具。 |
| Impeccable | [pbakaus/impeccable](https://github.com/pbakaus/impeccable) | 已审阅入口和 craft-floor。吸收可读性、状态、真实内容和有限轮次视觉检查；未运行其安装器、二进制或全局 hooks。 |
| GSAP | 已安装的 HyperFrames GSAP skill + [官方文档](https://gsap.com/docs/v3/) | 用于时间线、响应式媒体查询和清理；实现为网站自己的 Vue 生命周期逻辑。 |
| 高德地图 JSAPI skill | [AMap-Web/amap-skills](https://github.com/AMap-Web/amap-skills) | 已核实官方仓库和入口。当前只有 Hamilton 一家店，采用 [Google Maps URL](https://developers.google.com/maps/documentation/urls/get-started) 导航即可，不为单点到店导航增加地图 SDK 与密钥。 |

可复用适配 skill：`.agents/skills/pindou-studio-design/SKILL.md`。上游全文仅作为本地研究材料保存在被 git 忽略的 `artifacts/studio-research/`，不会作为网页内容或发布包上传。

## 本轮字体、按钮与排版修订

根据用户“英文字体保留、中文字体需重做、按钮参考 Turnitin”的反馈，读取当前 T-Check 工作树 `C:/Users/123/Desktop/Turnitin_generation/docs/FRONTEND_INTERACTION_AND_MOTION_STANDARD.md`，以及 `admin-dashboard/css/index.css`、`generate.html` 与 `v2-style.css` 中的实际规范和实现。未修改 T-Check 文件或服务。

- 主按钮悬停上移 2px，按下回落 1px 并缩至 0.988；按钮与箭头都使用 300ms ease-in-out，保持启动和结束同步。
- 采用圆角 13px、轻阴影和明确的焦点状态；纯信息区域不套用可点击卡片的浮起反馈。
- 相册统一顶部和图注对齐，取消无内容理由的交错偏移；商品说明和价格对齐；表单、文字间距和点击区保持可读尺寸。
- 中文正文与标题独立分工，使用真实可变字体而非合成字重。英文字体家族保留。
- 预约表按日期、开始 / 结束、人数的顺序排列；当天已过去的开始时间不显示，改变开始时间后修正失效的结束时间；单人 / 双人套餐对应 1 / 2 人。它仍是意向预约，不代表实时空位。

字体来源：[Google Fonts Noto Serif SC](https://github.com/google/fonts/tree/main/ofl/notoserifsc)、[Noto Sans SC](https://github.com/google/fonts/tree/main/ofl/notosanssc)，采用 OFL 1.1，许可随网站放在 `public/font-licenses/`。子集制作脚本 `05_studio/scripts/build-cjk-fonts.py`，源文件及产物校验值在 `05_studio/src/assets/fonts/manifest.json`。子集覆盖当前静态中文界面；顾客输入的其他罕见字使用系统后备字体。增加中文文案时应重新生成并核对字形覆盖。

## 照片来源

主来源：[小狗双吉 · Hamilton 拼豆屋](https://xhslink.cn/o/8HFIo1pstmk)。用户在本轮明确授权取图。
作者：[小狗双吉主页](https://www.xiaohongshu.com/user/profile/65f8375c000000000b00c921)。

`studio-01`–`studio-15` 对应主笔记顺序；`journal-XX` 对应采集时主页卡片的零起始序号。
图片按公开 CDN 原字节保存，不抹除原图标记，不用 AI 重画店内场景；布局需要时使用 CSS object-fit。
首屏使用无宣传文字的 `studio-02`，避免把有旧营业信息的封面作为主视觉。
