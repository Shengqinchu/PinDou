# Task A — 现有拼豆 / 像素化工具技术拆解

> 调研日期：2026-05-24  
> 范围：公开网页 + GitHub；未登录微信 / 小红书；未下载真实人像图。  
> 关联 GitHub 生态详见 `github_landscape.md`。

## 中文 / 小程序 / App 工具

| 工具 | 链接 | 技术 / 算法 / 商业化 | 可借鉴点 | 必须避开的坑 |
|------|------|----------------------|----------|--------------|
| 拼豆星球 | [pindou.cn](https://pindou.cn/) / [App Store](https://apps.apple.com/my/app/%E6%8B%BC%E8%B1%86%E6%98%9F%E7%90%83/id6756865487) | Web + App；支持 MARD / COCO / 漫漫 / 盼盼 / 咪小窝，10-300 格、去背景、色号、下载；有卡密 / VIP 群入口 | 覆盖国产色卡、社区、任务激励、图纸编号搜索 | 隐私项较多；PinDou 要强调最小化数据 |
| 颂拼豆 | [32r 页面](https://www.32r.com/app/143740.html) | Android；照片转色号图纸 + 手绘编辑 + 社区 + 商品导购；内购 | “自动生成后继续人工编辑”是正确工作流 | 页面教程提示自动图纸会有色差，说明纯自动不够 |
| 米粒拼豆 | [中华网报道](https://digi.china.com/articles/20260420/202604201850740.html) | 微信小程序；照片转图纸、图纸广场、像素化、仓库管理 | “图纸 + 库存管理”能提高复购 / 留存 | 公开技术细节少，需真机黑盒补测 |
| 拼豆农场 | [源码/SAAS 售卖页](https://www.1004619.com/66750.html) | 小程序 + 后端 + Web 设计中心 + 管理后台；AI 生成、创作者入驻、社区；1699 / 2999 / 13999 元套餐 | 证明市场有人买“完整生态”，创作者供给是方向 | 源码加密 / 授权模式复杂，不宜采购依赖 |
| 你萌好魔法拼豆 | [小程序商店页](https://www.dian68.net/portal/article/index/cid/46/id/17362.html) | 早期微信小程序；图纸查找、自制图案、照片转像素、自由绘制 | 老产品验证“图库 + 转图 + 画图”基本需求 | 年代久，算法 / 体验可能落后 |
| 拼豆大师 Pro / 365-Tools | [365 Tools](https://365-tools.cn/detail/40) | Web；Perler 标准色卡、RGB 欧氏距离、实时用量、PDF、图像增强 | 文档化好：用户痛点是色差、数量、施工图 | RGB 最近邻对肤色 / 实物感知不稳 |
| 德虎造物 | [dehumaker.cn](https://dehumaker.cn/) | Web 工坊；图纸转本地图纸 AI 识别、AI 生成、20+ 绘制功能、MARD / COCO / 漫漫 / 盼盼 / 咪小窝 | “图纸识别 / AI 生成 / 多品牌色卡”说明中文市场功能卷得快 | 涉水印去除功能，PinDou 应避开侵权诱导 |

待真机补测：`拼豆小师傅`、`一粒像素豆`、`拼豆图纸生成器 Pro` 未在公开网页检索中拿到稳定来源 URL，后续建议用微信内搜索 + 同图黑盒测试补齐。

## Web 工具

| 工具 | 链接 | 技术 / 算法 / 商业化 | 可借鉴点 | 必须避开的坑 |
|------|------|----------------------|----------|--------------|
| MakeBead | [makebead.com](https://makebead.com/) | 浏览器端；Perler / Hama / Artkal / Nabbi；weighted RGB；Floyd-Steinberg；PDF / PNG；免费 + 账号 / 广告 | 编辑、替换、进度追踪、多板 PDF 功能完整 | weighted RGB 不等于实物感知最佳 |
| Bitbead | [bitbead.pomodiary.com](https://bitbead.pomodiary.com/) | CIEDE2000；Perler / Hama / Artkal / MARD；免费无限；PNG / PDF | CIEDE2000 + 采购清单是强标杆 | 免费工具会压低用户付费预期 |
| BeadMapper | [beadmapper.com](https://www.beadmapper.com/) | 本地浏览器处理；Perler / MARD / Artkal / Hama / Nabbi；dithering；300x300 | 隐私卖点强，适合 PinDou 借鉴 | 算法细节公开少 |
| BeadPattern | [beadpattern.net/zh](https://beadpattern.net/zh) | AI 文生图 + 图片转图纸；PDF；免费 / 订阅 / 买断；月付 $4.98、年付 $29.90、买断 $39.90 | 定价结构可参考：免费水印 + Pro 无水印 / 大尺寸 | “AI 专为手工优化”需实测，不可照搬宣传 |
| PixelPerler | [pixel-perler-ai.com](https://pixel-perler-ai.com/) | AI 生成 + 背景移除 + 官方色卡 + PDF / 购物清单 | 路线接近 PinDou：AI 预处理后再生成图纸 | 公开细节少，需实测输出 |
| SimplePixelArt | [simplepixelart.com/convert](https://simplepixelart.com/convert) | 浏览器端 median-cut；4-64 色；孤点清理；非拼豆专用 | “Pixel Cleaner”非常值得做成后处理 | 缺真实豆色 / 色号，不可直接当拼豆竞品 |

公开检索未验证：`Beadr.app` 未找到稳定页面；`Pixelogic.app` 当前公开页面是 nonogram 游戏，不是拼豆图纸工具；`Perler 官方 pattern generator` 未找到稳定官方生成器入口，Perler 官方更像色卡 / 项目指南来源。

## Top 5 必须吸取的教训

1. 人像不能只做 resize + 最近邻量化：五官、肤色、头发边界会碎，必须先做主体 / 风格预处理。
2. 色差算法决定实物成败：RGB 最近邻够快但不稳，CIELAB / CIEDE2000 更适合真实豆色匹配。
3. “自动生成”之后必须允许手工修图：画笔、橡皮、替换颜色、撤销、孤点清理是刚需。
4. 用户买的是施工方案，不是像素图：PDF、色号、用量、分板、采购清单、进度追踪比预览图更重要。
5. 开源生态许可风险大：ComfyUI GPL、A1111 AGPL、Pixelization 非商用，最多参考思路，不能直接产品集成。

## 我们可直接借鉴的产品点

- AI 预处理输出必须和普通量化同屏对比，支撑 ADR-003 的付费转化假设。
- 材料清单要能按 MARD / COCO 切换，并给出总颗数、色号数量、估价、底板数。
- 量化输出后必须提供人工修正能力，至少包括单点改色、批量替换、撤销、孤点清理。
- 隐私卖点可以写入 PRD：浏览器本地处理基础量化，只有 AI 高级风格化才上传。
- 免费额度要非常清晰，否则会被免费工具压制；可参考“免费导出次数 + AI 次卡 / 月卡”。

## 样本说明

本轮未提交竞品实测输入 / 输出截图，原因：

- 微信小程序需要真机登录与上传测试图，当前会话无法保证授权链路。
- 真实人像图 commit 前必须问用户，本轮避免下载或提交真实人像。
- Web 端样本建议在 Task C 的合成 / 授权测试图确定后，用同一组图补测，存入 `competitor_samples/`。
