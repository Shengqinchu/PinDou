# PinDou 独立 Web 前端

Batch 0 只搭地基：Vite + Vue 3 + TypeScript + Pinia + vue-router History mode。

## 当前线上入口

- 正式 Web 域名：`https://pindoupuppy.com/`
- 浏览器端 API：同源 `https://pindoupuppy.com/api/v1`
- 验收、用户链接和截图统一使用主域；旧 staging 子域只作为临时兼容/回滚入口，不再作为对外口径。
- 当前生产域名由 Cloudflare Tunnel 指向上海移动云源站，Nginx 服务 `/opt/pindou/current/05_web/dist` 与 `/api/*`；Cloudflare Pages 仅作为 preview/备用发布路径，不是当前正式源站。

## Cloudflare Pages 配置

- Project root: `05_web`
- Build command: `npm ci && npm run build`
- Build output directory: `dist`
- Preview deployments: 使用 Cloudflare Pages 默认 branch preview；不要把 preview 直接替换生产域名。
- Environment variable:
  - `BACKEND_ORIGIN=https://pindou-backend-263102-4-1437642655.sh.run.tcloudbase.com`

## 路由与代理

- 浏览器端 API base 固定为同源 `/api/v1`。
- Pages preview 下 `/api/*` 由 `functions/api/[[path]].ts` 反代到后端，响应统一 `Cache-Control: no-store`；生产主域的 `/api/*` 由移动云 Nginx 反代到本机 FastAPI。
- Cloudflare Pages 项目不放顶层 `404.html`，使用 Pages 默认 SPA fallback 支持 vue-router History mode。
- `_routes.json` 只让 `/api/*` 触发 Pages Functions，静态资源保持 Pages 静态托管路径。

## 本地验证

```bash
npm install
npm run build
npm run cf:preview
```

打开本地 Pages preview 后访问 `/api/v1/user/profile` 应返回 `401`，说明同源代理链路连通。
