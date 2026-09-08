# PinDou Puppy Studio

Hamilton 小狗拼豆铺的独立双语工作室网站。开发预览：[pindoupuppy.com/studio](https://pindoupuppy.com/studio/)。

Vue 3 + TypeScript + Vite，GSAP 动效，Phosphor 图标，本地字体与店主授权照片。

```powershell
npm install
npm run dev
```

本地入口为 `http://127.0.0.1:5184/studio/`。预约 / 自提 API 代理到 `127.0.0.1:8011`，运行方法见 `../07_ops/STUDIO_DEPLOYMENT.md`。不要在开发过程中修改 `../05_web` 的生成器路由。

```powershell
npm run build
node scripts/verify.mjs
```

`verify.mjs` 用本地 API 创建明确的测试请求，测试数据应放在独立 QA 数据库。`verify-live.mjs` 验证公网页面、语言、动效、管理登录入口和旧生成器，不提交订单。

业务说明：`../02_product/STUDIO_V1.md`。
设计方向与来源：`../03_design/STUDIO_DESIGN.md`。
发布与回滚：`../07_ops/STUDIO_DEPLOYMENT.md`。
本轮验收：`../07_ops/STUDIO_VERIFICATION.md`。

主站正式切根路径前，需要确认经营资料，并保持旧 `/upload`、`/result/:id`、`/editor/:id` 等链接和 API 兼容。

## VISION2（2026-09-08）

当前设计与业务见02_product/STUDIO_VISION2_PROGRESS.md。文案集中于src/content，构建自动执行check:copy；未经店主明确要求，不得修改文案或刷新approved.json。后台“编辑预约规则”设置每组人数、总容量和每周营业时间。新文章导入脚本仅在店主提供链接并要求迁入时执行。主工具保留。最终发布验证见07_ops/STUDIO_VISION2_VERIFICATION.md。
