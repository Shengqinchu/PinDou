# 2026-09-09 生成器动效、逐字标题和价格角标

已发布 `20260909211553-studio-v7`，build `2026-09-09T21:05:10.485Z`，353 个文件哈希核验通过。归档 378,464 字节，SHA-256 `ef67a6a55d831878ec1f3a528de083e36ef915bbf237b05126d39836972ec994`；发布备份 `/opt/pindou/studio/backups/20260909211553-studio-v7/`。

## 实际上线范围

- 首页、预约、详情、日记、账号、生成器的主要标题接入 `LiftTitle`。Vue 维护字形节点，Latin 保留整词换行，使用 `Intl.Segmenter` 保持 Unicode 字形完整。标题使用完整 aria-label，视觉字形隐藏于读屏树；不改变原文或字号。字形和命中区分层，独立 560ms 上跳／回落，重入替换当前动画，切换语言、降动效、隐藏页签和销毁时清理。
- `MoneyText` 在预约价格卡和生成器 CNY 套餐／付款摘要中将币种排到数字右下侧。价格来源、币种、格式精度、后台覆盖和计费逻辑不变。普通段落中的积分／汇率说明不重排。
- 生成器所有按钮与按钮角色的控件接入主站短按补全；共用 300ms 曲线与按下／禁用／键盘／降动效处理。进入工具页面时轻微淡入位移，编辑画布的坐标、缩放和拖动保持原实现。
- 三步预约仅实现为本地可点击方案，源码位于 `05_studio/prototypes`；`prototype.html` 不在生产包中。正式 `/visit` 仍使用原有预约流程。

## 验证

`npm --prefix 05_studio run build` 通过文案锁定、TypeScript 和 Vite 构建；本轮不改经营文案哈希。

`verify-motion-proposal.mjs` 五组通过：单字中间帧位移与其他字静止、上跳回零、重入不堆积、布局尺寸不变、文字复制与中英文；CAD/CNY 的实际字号／位置；生成器 300ms 短按、状态即时生效和系统减少动态；主站 320/390/768/1024/1440/1920/2560px；三步方案前进／回退／切语言保留输入且不发真实预约、4 档宽度及 axe。JavaScript 错误 0，原型 axe 问题 0。

`verify-native-generator.mjs` 58 项端到端回归通过，覆盖上传、普通生成、AI 模拟任务、编辑、撤销重做、保存失败保留编辑、PNG 导出、弹窗焦点、作品／教程及多尺寸双语布局。全部运行在独立 loopback QA API／数据库，没有调用真实付费生成或支付。

生产审计：Studio 数据、共享生成器数据、钱包说明、已有余额与备注指纹均与发布前相同；两个服务 active；公网入口及标题／价格／生成器特性资源字节与构建一致，HTML no-store。旧生成器后端仍为 `20260909152214-studio-v6`，旧 HTML SHA `2f581f2b0db0df44ac39291edcc16c41ff9bfb63869e32f7b56a7c3d5564e131`。

当前 Codex 浏览器真实报告 `motionSource=system`、`systemMotion=reduced`，正式站据此保持静态。原型使用本地链接 `?motion=full` 演示完整动效，没有修改 Windows 设置或正式站偏好。不能把强制完整动效的测试当作系统默认启用了动画。

Codex 内置浏览器原型中另采样确认：指针进入标题首字后，首字处于约 -5.57px 的上浮中间帧；后两个字为 0，前一个已扫过的字已接近 0。命中区和字形是独立层，字符之间未共享整段平移。

## 原型与复现

- 方案：[STUDIO_VISIT_FLOW_PROPOSAL.md](../03_design/STUDIO_VISIT_FLOW_PROPOSAL.md)。
- 本地原型：[三步预约](http://127.0.0.1:19679/prototype.html?motion=full)。本轮为用户查看保留 19678 示例 API 与 19679 Vite 预览，均仅绑定 127.0.0.1。
- 需要重启时，在项目根使用已安装 Studio 依赖的 Python 运行 `06_studio/qa_generator.py`；在 `05_studio` 运行 `node node_modules/vite/bin/vite.js --config vite.prototype.config.ts --host 127.0.0.1`。
- 证据目录：`artifacts/visit-flow/`，包括逐字效果、CAD/CNY 价格、三步桌面／手机截图、浏览器检查和生产数据指纹。
