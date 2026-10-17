# PinDou 管理员后台 Brief（Phase 2 收尾）

> 决策人：用户 + chat 端 Claude。执行：Codex。验收：chat 端 Claude 逐批 review。
> 触发背景：2026-05-29 生产全链路 smoke test 通过，进入管理员后台。范围＝7 项全做。
> **本 brief 必须遵循用户的后台开发标准**（saas-playbook `spec/03-admin-dashboard.md` + `audit/architect-decisions.md` §C3/§C4）。关键强制项已内联在下方，Codex 无需访问 saas-playbook 也能实现。

## 标准强制项（不可省）

- **C3 危险操作必须审计**：任何改变用户资产（额度/月卡/订单状态/CDK）的操作 → 写 `admin_audit_logs`（actor、role、action、resource、before、after、reason、request_id、created_at）。
- **C4 密钥零落地**：任何接口/配置页绝不回传 secret（COS key / DB 密码 / JWT_SECRET / 微信 AppSecret），只回引用或状态。
- **三角色**：Day 0 至少 `admin` / `operator` / `viewer`。每个 API 声明所需角色，后端再次校验，权限拒绝返回明确错误（不得伪装空结果）。PinDou 现仅建一个 admin 账号，operator/viewer 端点先声明好角色、暂不建账号。
- **危险操作要 reason + 返回审计事件 ID**。
- **人工补发拆两步**：禁止"一键改已支付并发货"。必须分 ①确认支付事实 ②发放权益，各自审计、各自幂等。
- **登录**：独立登录、会话有过期、支持退出、token 不入 URL、登录失败限频、登录成功记审计。优先 HttpOnly+Secure Cookie；PinDou 历史用 JWT+localStorage，**必须在 FUTURE_WORK 写明兼容原因作为风险记录**。
- **回调可见**：订单详情展示回调日志、签名是否通过；金额不一致标红进人工审核；重复回调可见但不重复发放。
- **UI**：紧凑、表格优先、筛选贴近表格、危险按钮颜色区分、确认弹窗展示影响范围、JSON 可折叠。
- **隐藏菜单不删审计**：PinDou 隐藏 商品管理 / 支付通道写操作 / 任务 / 代理 / 邀请（无此层），但审计能力保留。

## 架构决策

- 后台单文件 `admin.html`（Vue3 CDN），FastAPI 当静态文件挂在不与 `/admin/*` JSON API 冲突的路径（建议 `/console/`，Codex 自定并在报告写清）。
- 浏览器打开该页 → `/api/v1/admin/login` 拿 admin JWT（payload 带 role）→ localStorage → 请求带 `Authorization: Bearer`。
- 后台 API 统一在现有 `/api/v1/admin/*` 命名空间，全部经 `require_role(...)` 依赖。

## 数据模型（已存在，勿改结构）

- **User**: openid, nickname, avatar, free_credits_remaining, paid_credits, monthly_card_expires_at, created_at
- **Artwork**: artwork_id, user_id, original_path, preview_path, pattern_json, style_preset, size_preset, tier, title, is_paid_unlocked, created_at, original_deleted_at
- **Order**: order_id, user_id, order_no, sku, amount_cny, status, payment_method, payment_provider, qr_code_path, paid_at, created_at, artwork_id, cdk_code
- **CDK**: code, type, value, status, redeemed_by, redeemed_at, sales_channel, batch_id, created_at, created_by, expires_at, notes

新增（本 brief）：**`admin_audit_logs`**（id, actor_id, actor_role, action, resource_type, resource_id, before_json(nullable), after_json(nullable), reason, request_id(nullable), created_at）。

## 批次划分（每批一个原子 commit，push origin/phase2，报 hash）

### Batch 1 — 审计地基 + 角色 + 只读 API + config
- 新增 `admin_audit_logs` 模型 + alembic migration 0003（create_all 自动建表，migration 补上保持一致）
- 写审计 helper：`write_audit(actor, role, action, resource_type, resource_id, before, after, reason, request_id) -> audit_id`，仅后端可调
- JWT payload 加 `role`；新增 `require_role(*allowed)` 依赖；现有 `/admin/login` 校验通过的用户给 role=admin
- 登录：失败限频（同 IP/账号窗口内次数上限）+ 登录成功写审计（action=`admin.login`）
- 只读 API（全经 require_role，列表统一返回 {items,total,page,size} + 稳定排序）：
  - `GET /admin/orders` 分页，filter status，search order_no/user_id
  - `GET /admin/orders/{order_no}` 详情，**含回调日志/签名是否通过/金额是否一致/是否重复回调**
  - `GET /admin/cdks` 分页，filter status/type/batch_id
  - `GET /admin/users` 分页，search openid/nickname，含 artwork 数
  - `GET /admin/users/{openid}` 详情 + 最近 10 单 + 作品数
  - `GET /admin/artworks` 分页，filter user_id；preview_path 以 /static/ 开头标 legacy_preview=true
  - `GET /admin/config` 只读，公开/敏感分离，敏感只回引用或状态，**绝不回 secret**
- pytest：每接口正常路径 + 非 admin/越权 token → 401/403

### Batch 2 — 危险写操作（全部 reason + 写审计 + 返回 audit_id + 幂等）
- 订单人工补发拆两步，禁止一键改已支付：
  - `POST /admin/orders/{order_no}/confirm-payment-fact` {reason} → 仅标"已确认收到款"，写审计，幂等
  - `POST /admin/orders/{order_no}/grant-entitlement` {reason} → 发对应权益（额度/月卡/解锁作品），写审计，幂等（已发不重发）
- `POST /admin/users/{openid}/credits` {delta_free?, delta_paid?, set_monthly_card_days?, reason(必填)} → 结果不得为负；写 before/after 审计；返回调整后余额 + audit_id
- `POST /admin/cdks/batch` {type, value, count, sales_channel, expires_at?, notes?} → 同 batch_id 生成唯一码，created_by=当前 admin，写审计，返回 codes + audit_id
- `GET /admin/cdks/export.csv?batch_id=&status=` → StreamingResponse CSV
- webhook 幂等核对：重复回调记录可见但不重复发放（如现状未做则补）
- pytest 覆盖

### Batch 3 — admin.html 外壳 + 登录 + Dashboard + 订单页
- 新增 `06_backend/pindou/static_admin/admin.html`（Vue3 unpkg，单文件，纯 fetch），main.py 挂载（路径不冲突，自定）
- 登录页 → /admin/login → JWT localStorage；401 自动回登录页；支持退出
- Dashboard：用户数、今日订单、支付成功率、异常订单数、最近危险操作（读审计）
- 订单 Tab：表格 + status 筛选 + 分页 + 详情（回调日志/签名/金额不一致标红）+ 两步补发按钮（危险色 + 确认弹窗展示影响范围）
- UI 遵循标准 §15（紧凑、表格优先、JSON 可折叠）

### Batch 4 — 其余 Tab
- CDK：批次/库存/状态/兑换记录 + 批量生成弹窗 + 导出 CSV
- 用户：搜索 + 详情抽屉 + 额度调整表单（reason 必填，调整 >100 二次确认）
- 作品：列表 + user 筛选 + 缩略图 + legacy_preview 红标
- 配置：只读，公开/敏感分离展示
- 审计日志：列表 + 筛选 + before/after JSON 可折叠

### Batch 5 — admin.html UI 换皮（复刻 T-Check 设计语言）
- 背景：Batch 3/4 功能全对，但裸 HTML 太丑、首屏甩 JSON 不专业。用户指定复刻参考 UI。
- 参考文件（Codex 直接打开抄设计系统）：`C:\Users\123\Desktop\AI_Test\v2\admin.html`
  - 技术栈：Bootstrap 5.3 + Font Awesome 6 + Chart.js（均 CDN，零构建）
  - 配色 :root —— primary #4f46e5 / light #6366f1 / bg #eef2ff / success #10b981 / warning #f59e0b / danger #ef4444 / gray 50–900；sidebar 260px；卡片 radius 16px；柔阴影
- 原则：**只换皮，不动逻辑**。Batch 1–4 的 fetch/token/401/两步补发/额度>100二次确认/reason必填/审计/JSON折叠全部保留不变。
- 布局复刻参考：
  - 左侧栏 260px：品牌「PinDou Admin」+ 分组带 FA 图标导航（概览：Dashboard；管理：订单/CDK/用户/作品；系统：配置/审计）+ 底部用户卡（admin + 角色 + 退出）
  - 顶部面包屑
  - Dashboard：彩色图标统计卡（总用户/今日订单/支付成功率/异常订单/CDK总量/已用CDK）+ 2 个 Chart.js 图表（近7天用户增长折线 + 近7天订单柱状）；**移除首屏裸 Dashboard JSON dump**
  - 各 Tab 表格→Bootstrap 表格，危险按钮→btn-danger，确认弹窗→Bootstrap modal
- 图表数据：若 GET /admin/dashboard 没有近7天序列，补只读字段（按天 用户增长 + 订单数），require_role 不变。

## 全局约束
- Batch 1/2 只动 `06_backend/`；Batch 3/4 动 `06_backend/pindou/static_admin/` + main.py
- 不改小程序前端 `05_frontend/`；不改 `.env`
- 每批：跑 pytest（后端批）/构建确认（前端批）→ git add 指定文件 → commit → push origin/phase2 → 报 hash + 改动文件 + 验证结果 + 新增路由
- 跑测试用 sqlite 覆盖 DATABASE_URL，勿连云内网 MySQL
