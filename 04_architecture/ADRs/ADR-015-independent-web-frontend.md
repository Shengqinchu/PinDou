# ADR-015 独立 Web 前端 05_web（从 uni-app H5 切出）

- 状态：**已采纳并定稿**（2026-06-01；用户拍板 B + Codex 评估 Go + chat 端 Claude 审查接受）
- 决策人：用户方向（B）→ Codex 评估（Go，挑出 CORS/限频IP/QR相对URL/_redirects/HEIC 等真问题）→ chat 端 Claude 审查接受 + 强调 CF 在华延迟风险
- 触发：uni-app H5 持续拧巴——登录/上传/tab/路由/静态包路径混合了小程序运行时与浏览器运行时；H5 产物要同步 static_h5 经云托管/Cloudflare 缓存发布，线上常跑旧包；邮箱登录/上传授权问题本质是 "uni-app H5 + 静态缓存 + 旧 token/旧 bundle" 组合症。Web 体验对小红书/手机浏览器用户会越来越重要。

## 决策（倾向）：方案 B——新增独立 `05_web`，`05_frontend` 专注小程序

- 技术栈：Vite + Vue 3 + TypeScript + Pinia + vue-router（History mode）
- 直接调现有 FastAPI `/api/v1/*`，**前端永远打同源 `/api/v1`**，由 Cloudflare Pages Function 反代到腾讯云托管 → 不依赖 CORS（代码默认 CORS 是 localhost 列表，prod env 当前为 `*`，但同源代理后这点无关紧要）。邮箱登录接口已落地。
- 小程序继续用 uni-app（05_frontend），不再强行共用 H5
- H5（uni-app 的 web 产物）切出后可逐步弃用

## 现状事实（已核对，供评估基线）
- **后端邮箱登录已存在**（commit e01e7ec）：`POST /user/email/send-code`、`POST /user/email/verify`、`EmailVerificationService`（Resend，复用 essayaipass 域）。05_web 可直接对接。
- `05_frontend/src/api/index.ts` **有 uni.* 依赖（5 处，上传/callContainer）** → 类型定义可复用、请求实现必须重写。
- 域名 pindoupuppy.com 已在 Cloudflare。

## 复用 vs 重写
| 可复用 | 必须重写 |
|---|---|
| API TypeScript 类型定义 | 请求实现（uni.request/uploadFile/callContainer → fetch/XHR） |
| Design tokens（colors_and_type.css）| 路由（pages.json → vue-router） |
| DESIGN.md（Clay）| 存储（uni.setStorageSync → localStorage） |
| 业务常量（sku/套餐/色号映射）| 选图（uni.chooseImage → `<input type=file>`） |
| 结果轮询逻辑（去 uni 后） | toast/loading/tabBar（原生组件）；删所有 #ifdef |

## 部署：Cloudflare Pages（含 Codex 评估修正）
- pindoupuppy.com → Cloudflare Pages（05_web 构建产物），Git push 自动构建+部署，缓存自动失效（治"线上跑旧包"根因）
- `/api/*` → **Cloudflare Pages Function**（不是 `_redirects`！`_redirects` 对 Function 不生效）反代 → 腾讯云托管后端；前端同源打 `/api/v1`
- **SPA fallback（History mode）必须排除 `/api/*`**，别让 fallback 把 API 吃掉
- **缓存纪律**：API 响应 `no-store`；hashed assets 长缓存；`index.html` 不长缓存
- 主域已确定为 `https://pindoupuppy.com/`；后续验收、截图和用户链接统一使用主域。
- 不用 FastAPI 挂载（改前端要重部署后端，是旧包问题来源）
- ⚠️ **CF 在华延迟风险**：Cloudflare 免费版对国内线路可能限速/抖动。**必须用国内手机网络实测加载速度**；规模化投放时大概率需"国内 CDN + ICP 备案"（回到 ICP 墙）。

### 实际部署（2026-06-01 修订，2026-06-05 主域口径更新）
- **决策修正**：原写"不用移动云"。实际采用 **移动云 Web 源站 + Cloudflare 代理/Tunnel** 暴露：cloudflared 出站隧道，源站不开入站 80/443 端口 → 规避工信部"扫开放端口封未备案站"的执法 → **未备案也能跑**（chat 端 Claude 此前把"大陆服务器必须备案否则封端口"说死了，忽略了 Tunnel，已纠正）。
- 现状：`https://pindoupuppy.com/` 是正式 Web 入口；`/api/v1/user/profile` 应返回 401，表示同源代理通。旧 staging 子域只作为临时兼容/回滚入口，不再作为对外验收口径。
- **合规风险（记牢）**：Tunnel 是"技术可跑"的规避，非合规。收钱+小红书放量的消费产品长期无 ICP 仍有风险（举报/做大被注意/支付与平台合规）。**早期 OK，规模化前正经备案**。
- **延迟**：Tunnel 不改善"用户→CF 边缘"这跳的在华延迟（域名仍解析到 CF），国内手机实测速度仍必做。

## 后端 web 友好补丁（Codex 评估，Batch 0/对应批次随手补）
- 限频识别 `CF-Connecting-IP` / `X-Forwarded-For`（现在多处只用 `request.client.host`，套 CF 后全是 CF 边缘 IP，限频失效）
- 支付 QR：后端返绝对 URL 或前端统一 resolve（payment.py 非 mock 现返回相对 `/payment/order/{no}/qr.png`）
- 上传 413 / 格式错误 友好提示（后端已支持 multipart/10MB/jpg-png-webp）
- 图纸/预览/缩略图已是 COS 绝对 URL（STORAGE_BACKEND=cos），跨源 OK；仅 QR 与残留 /static 需统一 URL 规则

## Phase 1 批次（Codex 评估版，前加 Batch 0 地基）
- **Batch 0（地基）**：05_web 骨架（Vite+Vue3+TS+Pinia+router）、fetch API client（同源 /api/v1 + Bearer + 401重登）、env、Cloudflare Pages preview、`/api/*` Pages Function 代理、SPA fallback（排除 /api）、token storage、基础错误处理。**验收**：preview 域能打开，`/api/v1/user/profile` 401 正常返回，不走旧 /h5。
- **Batch 1**：邮箱登录 + 我的账户 + 路由守卫。**验收**：发码、登录、刷新保持、退出、401 回登录。
- **Batch 2**：首页 + 上传（file input+预览）+ 生成选择 + loading + basic result。**验收**：手机浏览器上传图、生成图纸、结果页看图/色号。
- **Batch 3**：作品集 + Paywall + 虎皮椒 QR + CDK + premium/partitions。**验收**：下单、QR 展示、轮询、CDK 兑换、作品详情闭环。
- **Batch 4（可选）**：SEO/meta、错误监控、缓存策略、旧 /h5 下线 + 回滚文档。

## 路由：History mode（URL 干净、利于 SEO）；SPA fallback 经 Pages Function 处理且排除 /api

## 风险清单（Codex + Claude）
- 两份前端类型/设计漂移 → 后续从 FastAPI OpenAPI 生成 TS 类型，减少手抄。
- Web 上传复杂度：移动 Safari、微信/小红书内置浏览器、**HEIC（iPhone 默认）**、大图压缩、EXIF 旋转、内存峰值——Batch 2 重点。
- /static、支付 QR、pattern PNG/JSON 统一 URL 规则。
- CF 缓存不能缓 API 和 index.html。
- **CF 在华速度/稳定性须实测；ICP 仍是正式投放风险**。
- 保留旧 /h5/ 作回滚入口，05_web 跑通真实"上传-支付-作品"闭环后再隐藏。

## 未决
- ICP：pindoupuppy.com 正式对国内服务仍需备案（同 ADR-014），先做出来；CF-在华若慢，提前规划国内 CDN+ICP。
- 05_frontend：从此只服务小程序；uni-app H5 仅短期保留回滚，闭环验证后下线。
