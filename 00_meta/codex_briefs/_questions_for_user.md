# Questions For User

## 2026-05-24 — Task C API PoC follow-up

已处理：

- P1 `gpt-image-2` key 已通过本地 `.env` 补齐。
- P1 真实 API 已跑通 40/40 样本，结果见 `01_research/tech/poc_results.csv`。
- 量化输出图已生成，投票模板见 `01_research/tech/subjective_vote_template.csv`。

用户问题处理结论：

1. Q1 已解决：`.env` 已有 P1 key，P1 `gpt-image-2` 已跑通。
2. Q2 已确认：火山即梦 / 阿里通义万相本阶段跳过，P2/P3 留作 Phase 2 备选 provider 评估。
3. Q3 已确认：5 人主观投票由用户线下组织；Codex 只交付 `subjective_vote_template.csv` + `poc_samples/` 完整图集，投票数据回来后再汇总平均分与通过率。

## 2026-05-24 — Task H schema / Phase 1 PRD handoff

需要用户 / Claude 在 Phase 1 PRD 阶段确认：

1. 价格 schema 是否拆出独立 SKU 表？Task H 已出现 CNY / USD / EUR 混合价格样本，继续放在 `price_per_1000pcs` 会丢失币种、包装规格、平台和采集时间。建议 Phase 1 新增 `bead_skus`：`brand + bead_diameter_mm + code + platform + currency + pack_count + price + captured_at`。
2. `stock_status` 是否允许 `unknown` / `unverified`？公开源经常只能确认“色号体系存在”，不能确认某个豆径当前在售。当前 Task H 为了不改 schema，仍用 `common/rare` 并在 `notes` 里说明置信度。
3. Phase 1 PRD 衔接建议：`PatternBuilder.build(preview, size, brand, bead_diameter)` 先只开放 `MARD 5mm` 作为默认生产路径；后台可读取 Task H 的全库做隐藏实验，但 UI 不要让用户切 Hama/Perler/Artkal，直到 SKU 表、币种和实物色卡校准完成。

## 2026-05-24 — Task I China deep-dive PRD impact

给用户 / Claude 的 Phase 1 PRD 建议：

1. 默认色卡仍建议先用 MARD，但不要只写“MARD 5mm”。国内公开 SKU 和工具语境明显偏 `MARD/COCO/黄豆豆/DODO 2.6mm 小豆`，建议 Phase 1 默认文案改成“入门默认 MARD 5mm；人像/宠物隐藏实验 MARD 2.6mm”。
2. Task H 缺 `漫漫 / ManMan` 独立色卡。中文工具（拼豆星球、德虎、metamo）常见五件套是 MARD / COCO / 漫漫 / 盼盼 / 咪小窝，Phase 1 前建议补 `manman_*` 或确认映射。
3. Schema 建议新增：`bead_skus`（平台 SKU 表）、`china_market_status`（active / low_stock / discontinued_cn / new_release / unknown）、`aliases_cn`（中文别名）、`source_confidence`（每字段置信度）。不要把这些硬塞进现有 palette row。
4. 小红书 ≥200 篇完整样本需要用户 App 内人工补采；Codex 已交付 `xhs_manual_collection_template.csv`。未登录公开 Web 只适合入口和少量卡片线索，不应为凑量绕平台限制。
5. UI 色号搜索建议支持“奶白、腮红粉、描边黑、透色、黑白补充包”等中文口语词；材料清单仍显示品牌官方 code，别名只作为辅助搜索/展示。

## 2026-05-24 — Phase 2 backend task 0 review

任务 0 已完成服务器硬件盘点与低风险安全加固，结论给用户 / Claude review：

1. 上海生产机实测为 Ubuntu 22.04.5 LTS，8 vCPU，15 GiB RAM，系统盘 80G；`/dev/sda1` 与 `/var` 同盘。旧服务清理后当前约 79G total / 6.9G used / 69G available。
2. 硬盘低于 brief 的 100GB 阈值。当前已释放约 15G，MVP 短期可继续开发；上线前仍建议二选一：A. 接对象存储（OSS/COS/七牛）；B. 扩容到 ≥200GB 再允许用户原图/Preview 长期落本地盘。
3. 已完成 SSH key 认证：本地 `.env` 已切到 `PINDOU_PROD_SSH_USER=pindou` + `PINDOU_PROD_SSH_KEY_PATH`，旧 `PINDOU_PROD_SSH_PASS` 已移除；服务器已禁用密码登录，root 仅保留 key 登录应急。
4. 已创建 `pindou` 部署用户，启用 fail2ban，并启用 UFW：公网入站只允许 `22/80/443`。
5. 旧服务清理：已停用并移除 `claude-shop`、`cloudflared`、Docker `wxhm/new-api`、旧 Nginx 站点、`rpcbind`；已删除 `/opt/claude-shop`、`/root/new-api-data`、`/root/apisell`、`/root/wxhm-data`、`/var/lib/docker`、旧静态站点和缓存日志。
6. 当前端口：公网仅 SSH `22` 在监听；`80/443` 在 UFW 预放行但 Nginx 当前 inactive，等 PinDou 部署时重新启用。另有 `127.0.0.1:31088` 云探针，仅本机监听。

## 2026-05-25 — Phase 2 backend task 1 review

任务 1 已完成后端骨架与本地验证，结论给用户 / Claude review：

1. 已创建 `06_backend/` FastAPI 项目骨架，包含 `pyproject.toml`、`requirements.txt`、后端 `.env.example`、`pindou/` 包结构和 `tests/`。
2. 已按 PRD §5 保留 `PreviewProvider.generate(...)`、`PatternBuilder.build(...)`、`PatternSheet`、`ColorRef` 等契约轮廓；本任务只做占位，不实现业务逻辑，不改字段名。
3. 已用 `pydantic-settings` 实现配置加载，读取根目录 `.env` + `06_backend/.env`，密钥字段使用 `SecretStr`，没有把 key 写进 commit。
4. 本地 `.venv` 已安装核心依赖；`pytest` 通过；`uvicorn pindou.main:app --host 127.0.0.1 --port 8000` 已验证 `/health` 返回 `{"status":"ok"}`。
5. 服务器 UFW 已重新执行放行并启用：`22/80/443` allow，`ufw status verbose` 为 active；实际监听仍只有公网 SSH 与本地云探针。
6. 待 review 后进入任务 2：实现 `XiaochiGptProvider` + fallback chain，并开始接 PRD §5.1 的真实 PreviewProvider。

## 2026-05-25 — Phase 2 backend task 2 review

任务 2 已完成 PreviewProvider 实现，结论给用户 / Claude review：

1. `StylePreset` 已按 Gemini 前端 `05_frontend/api/index.ts` 对齐为 `q_portrait` / `q_pet` / `q_couple` / `cartoon_fallback`；`SizePreset` 保持 `60x80` / `80x100` / `100x120`。
2. 已实现 `XiaochiGptProvider`：通过 openai SDK 调反代 `gpt-image-2`，单次 90 秒超时，失败重试 1 次，第二次带不同 seed hint；prompt 采用 Task C 的 Q 版拼豆约束，重点限制“不补腿脚 / 不补身体 / 不加额外物体 / 去水印和背景杂物”。
3. 已实现 `PreviewProviderChain`：主 provider 失败后走 backup，最后走 `FallbackProvider`；chain 会累计 `fallback_count` 并记录失败 provider。
4. 已实现 `FallbackProvider`：调用 `PatternBuilder.build(raw_image=...)`，并把 `PatternSheet.grid` 渲染为 PNG preview。注意：真实 `PatternBuilder` 仍在任务 3 实现，本任务测试里用 fake builder 验证 fallback 逻辑。
5. 已实现 ADR-007 反代健康检查：FastAPI lifespan 启动后台 monitor，每 `REVERSE_PROXY_CHECK_INTERVAL_SECONDS` 检查 `REVERSE_PROXY_HEALTH_URL`，连续 3 次失败且累计超过 `REVERSE_PROXY_ALERT_AFTER_SECONDS`（默认 21600 秒 / 6 小时）写 error 日志告警。
6. 已补测试：mock OpenAI 调用验证重试；验证 primary success、backup success、quantize fallback 三条路径；验证 ADR-007 三次失败触发告警。`pytest` 通过 7/7。

需要 Claude / 用户确认的接口衔接点：

1. PRD §5.1 原始 `PreviewResult` 写的是 `image: bytes`，Gemini 前端类型写的是 `preview_id + image_url`。当前实现兼容两边：provider 内部保留 `image` bytes，`to_frontend_dict()` 只输出前端 7 个字段。任务 5 API 落地时建议保存 PNG 到 `PINDOU_PREVIEW_DIR`，再返回真实 `image_url`。
2. `cost_estimate` 目前为 `0.0`，因为反代实际计费单价未进入配置。若产品页要展示成本或后台要统计毛利，建议任务 5/7 增加 `XIAOCHI_GPT_IMAGE_COST_CNY` 配置项。

## 2026-05-25 — Phase 2 backend task 3 review

任务 3 已完成 PatternBuilder 核心算法，结论给用户 / Claude review：

1. 已实现 `PatternBuilder.build(...)` 双路径：`raw_image` 走脚本量化，`preview` 走 alpha 透明背景识别后量化；输出 `grid` / `color_counts` / `bead_total` / `coords` / `no_bead_mask` / `palette_used` / `estimated_cost_cny` / `brand` / `bead_diameter_mm`，并提供 `to_frontend_dict()` 转换为前端 `ColorRef | null` grid。
2. 已实现默认 MARD 5mm 色卡加载：`01_research/colormap/{brand}_{diameter}mm.json` → `ColorRef`，并用 `lru_cache` 避免重复 IO；价格估算暂用色卡里的 `price_per_1000pcs` 字段。
3. 已复用 Task B 的 `algorithm_impls/quantize_core.py`：生产量化路线为 K-means + CIEDE2000 + 无抖动；仅把 `skimage` 指标统计 import 延后到 `metric_values()` 内部，避免后端运行时引入不需要的离线 benchmark 依赖。
4. 已实现拼豆后处理：小于 3 格的孤立色块合并到色差最近的相邻颜色；黑色/近黑色轮廓受保护，不被合并；preview alpha < 0.5 标记为 `NoBead`。
5. 已实现基础 PNG exporter：把 `PatternSheet` 渲染为圆点状网格图；PDF / Excel / 分区图保留 stub，等高级包任务继续做。
6. 已回归 task 2 fallback：`FallbackProvider` 现在用真实 `PatternBuilder` 端到端出 PNG，不再依赖 fake builder。
7. 已补 `XIAOCHI_GPT_IMAGE_COST_CNY` 配置项，默认 0.0；`XiaochiGptProvider` 的 `cost_estimate` 改为读取该配置。
8. 已补测试：Task B 三张合成图回归、preview alpha NoBead、100x120 热路径性能、fallback chain 真实 PatternBuilder。`pytest` 通过 10/10。

需要 Claude / 用户确认的衔接点：

1. `raw_image` 路径当前不自动抠背景，默认整张图都转成豆子；`preview` 路径通过 alpha 做 NoBead。若脚本免费路径也要“白底自动不铺豆”，建议 task 5 前补一个明确规则：按边缘连通白/近白背景 flood-fill 成 NoBead，或要求用户先走裁切/去背景。
2. 当前 `estimated_cost_cny` 依赖 Task H 的 `price_per_1000pcs`，但该字段没有币种和 SKU 来源精度。Phase 1 可用作粗估，正式购物清单仍建议等 Task I 建议的 `bead_skus` schema。

## 2026-05-25 — Phase 2 backend task 3.1 review

micro-task “脚本路径试试自动去白底”已完成，结论给用户 / Claude review：

1. `PatternBuilder.build(...)` 已新增 `auto_remove_white_bg: bool = False`，默认值保持脚本路径原行为：整张图满铺，不识别背景。
2. 该参数只在 `raw_image` / script 路径生效；`preview` / AI 路径仍只走已有 alpha 透明背景逻辑，不调用白底检测。
3. 已实现 `detect_and_remove_white_bg(image, tolerance_delta_e=8.0)`：四角 5x5 均值到纯白的平均 CIEDE2000 小于 8 时，才从四角 flood fill；扩散阈值为 ΔE < 15，连通白底像素 alpha 置 0。
4. `PatternSheet.metadata` 已增加 `white_bg_detected`（snake_case）和 `auto_remove_white_bg_requested`。前端 / quota 层可用 `white_bg_detected=True` 才扣白底配额；检测失败时返回正常满铺图纸且不扣配额。
5. 已补测试：白底检测成功、非白底跳过且不修改图像、ΔE≈8 边界、默认 raw 行为不受影响。`pytest` 通过 13/13。

## 2026-05-25 — Phase 2 backend task 4 review

任务 4 已完成 SQLAlchemy 数据模型、Alembic migration、业务 service 与 ADR-009 原图清理任务，结论给用户 / Claude review：

1. 已定义 `User` / `Artwork` / `Order` / `CDK` / `ConsentLog` / `DailyQuota` ORM 模型；内部用户唯一键保留微信 `openid`，对前端输出时映射为 PRD / Pinia 使用的 `user_id`。
2. 已初始化 Alembic，并新增 `0001_phase2_models` migration，创建核心表、唯一约束和索引：`users.openid`、`orders.order_no`、`cdks.code`、`daily_quotas(user_id,date)`。
3. 已实现 `UserService`：注册 / 登录、隐私与敏感信息同意留痕、每日额度查询。
4. 已实现 `ArtworkService`：保存、列表、删除；删除作品时同步删除原图文件，符合 ADR-009 私人素材边界。
5. 已实现 `CDKService`：18 位安全字符生成、兑换、权益写入；同用户 1 分钟第 4 次兑换阻断，同 IP 10 分钟第 5 次兑换写 warning 告警。
6. 已实现 `PaymentService`：客服扫码订单创建与状态机（pending_cs_qr → paid_confirmed / cancelled，paid_confirmed → refunded）。
7. 已实现 `delete_expired_originals_once()` 与 FastAPI lifespan 后台 scheduler：默认 30 天后删除原图并写 `original_deleted_at`，调度间隔默认 86400 秒。
8. 已补测试：模型 CRUD / 前端字段映射 / CDK 防滥用 / 支付状态机 / 30 天原图清理；`pytest` 通过 20/20，Alembic `upgrade head` 在临时 SQLite DB 验证通过。

需要 Claude / 用户确认的衔接点：

1. PRD §6.1 写明 `bead_skus.json` 是来自 Task I 的独立文件，本次没有把 `bead_skus` 做成 SQL 表。若 task 7 购物清单需要后台管理 SKU，建议再开 migration 增加 `bead_skus` 表。
2. CDK 频率限制当前是进程内内存实现，足够支撑本地 / 单 worker P0；多 worker 或多机部署前建议改为 Redis / 数据库 attempt log。

## 2026-05-25 — Phase 2 backend task 5 review

任务 5 已完成后端 MVP API 主体闭环，结论给用户 / Claude review：

1. 已实现统一错误格式 `{error, message_cn, details?}`，并新增错误码字典：鉴权、合规同意、额度、上传、图纸、Preview、CDK、订单、校验错误等均走同一响应结构。
2. 已实现 JWT 鉴权：小程序用户 token 与 admin token 分开；普通路由从 `Authorization: Bearer` 注入当前用户，`/api/admin/*` 只能用 admin token。
3. 已实现上传端点：`POST /api/upload`，校验敏感信息同意、10MB 限制、jpg/png/webp、EXIF 旋正，保存到 `PINDOU_UPLOAD_DIR`，返回 `image_id` / `image_url`。
4. 已实现生成端点：`POST /api/generate/script` 走 `PatternBuilder(raw_image=...)`；`POST /api/generate/ai` 走 `PreviewProviderChain → PatternBuilder → Artwork`；另补前端兼容 `POST /api/v1/preview/generate`，返回纯 `PreviewResult`。
5. 已实现图纸端点：`POST /api/pattern/build` 支持前端 multipart raw_image 和 JSON preview_id；`GET /api/pattern/{artwork_id}` 返回保存的 PatternSheet JSON。
6. 已实现作品集端点：列表、详情、删除；删除沿用 task 4 `ArtworkService` 同步删原图。
7. 已实现用户、支付、CDK、admin 端点：`/user/login`、`/user/profile`/`/user/me`、`/user/consent`、`/payment/order/create`、`/payment/order/{id}`、`/payment/customer-service`、`/cdk/redeem`、`/admin/login`、`/admin/orders`、`/admin/payment/confirm`、`/admin/cdk/batch_generate`、`/admin/users`。
8. 已兼容前端当前 `BASE_URL=/api/v1`：同一套 router 同时挂载 `/api` 和 `/api/v1`；`/payment/order/create`、`/payment/customer-service`、`/user/profile` 均可直接对接前端现有调用。
9. 已补 `python-multipart` 依赖，并将 `06_backend/var/` 加入 `.gitignore`，避免上传图、preview、pattern JSON 误入 git。
10. 已补 API 测试：用户 / 上传 / pattern / generate script / generate AI preview / artwork / payment / admin / CDK 的 happy path 与错误路径；`pytest` 通过 27/27。

需要 Claude / 用户确认的衔接点：

1. 前端 `05_frontend/store/artwork.ts` 调用了 `api.generateAIPreview(...)`，但 `05_frontend/api/index.ts` 里实际函数名是 `generatePreview(...)`。后端已支持前端函数内部访问的 `/api/v1/preview/generate`，但 TypeScript 方法名不一致需要 Gemini / 前端侧补 alias 或改调用。
2. 当前微信登录是 Phase 2 dev stub：用 `code` 派生稳定 openid；正式接微信接口时需要在 task 8 或 Phase 3 接 `jscode2session`。
3. admin 默认账号密码只在 `APP_ENV=development` 时允许 `admin/admin`；生产必须配置 `ADMIN_USERNAME` + `ADMIN_PASSWORD_HASH`。

## 2026-05-25 — 用户回复：本机局域网 IP（给前端 mobile 适配 + 后端连接任务用）

用户 ipconfig 输出：
- `IPv4 地址 . . . . . . . . . . . . : 192.168.2.40`（**这是宿主局域网 IP，写入前端 DEV_API**）
- `自动配置 IPv4 地址  . . . . . . . : 169.254.83.107`（link-local fallback，忽略）

**Codex 前端任务 2 实施时**：
- `src/utils/request.ts` 的 `DEV_API` 改为 `http://192.168.2.40:8000/api/v1`
- 后端 `uvicorn` 启动时需要 bind `0.0.0.0`（不能只 `127.0.0.1`，否则局域网访问不通）：
  - 改为 `uvicorn pindou.main:app --host 0.0.0.0 --port 8000 --reload`
  - 或者在 `06_backend/pindou/main.py` 的 startup 配置里写死 host=0.0.0.0
- Windows 防火墙：可能需要允许 8000 端口入站（如果 Codex 改了上面但小程序还是 timeout，让用户加防火墙规则）

**额外提醒**：用户在小红书 / 闲鱼引流后真机扫码测试时，IP 必须是与微信开发者工具同局域网；不在同网就要走域名（FUTURE_WORK 第 2 条备案）。

## 2026-05-25 — Phase 2 frontend emergency task review

UI 多机型适配 + 后端连接配置 + 首页 CTA 半透明 bug 已完成，结论给用户 / Claude review：

1. 已新增 `03_design/wireframes/MOBILE_ADAPTATION.md`，落档状态栏 / 微信胶囊 / 底部安全区三层模型、iPhone SE / 12-13 / 14 Pro Max 尺寸检查点、rpx 换算和推荐 API。
2. `App.vue` 启动时已调用 `userStore.initDeviceMetrics()`，读取 `uni.getSystemInfoSync()` 与 `uni.getMenuButtonBoundingClientRect()`；失败时使用保守默认值，不阻塞首屏。
3. `MiniProgramLayout.vue` 已通过 CSS variables 接收运行时指标；标题栏按真实胶囊 `top/height` 对齐，并为右侧原生胶囊预留宽度，避免“上传你的照片”等标题压到 `...` 胶囊。
4. `components.css` 已去掉固定 375x667 frame，改为 `100vw/100vh`；正文高度按 `topChromeHeight` 与 `safeAreaBottom` 计算，并补 `env(safe-area-inset-bottom)`。
5. 后端 BASE_URL 已从 `127.0.0.1` 改为 dev/prod 可切换：dev 默认 `http://192.168.2.40:8000/api/v1`，prod 默认 `https://api.pindou.cn/api/v1`；也支持 `pd_api_base_url` storage override。
6. `src/manifest.json` 仍保持 `mp-weixin.setting.urlCheck=false`；同时已把微信工具实际读取的 `project.private.config.json` 里的 `urlCheck` 改为 `false`。
7. 首页 CTA 半透明修复：`navigator` 已设置 `hover-class="none"`，并在 `.home__cta` 显式保持 `opacity: 1` 和 `background: var(--pd-gradient)`。
8. 验证：`npm run build:mp-weixin` 通过；`npm run dev:mp-weixin` 已重新生成 `dist/dev/mp-weixin`。dev 产物确认包含 `http://192.168.2.40:8000/api/v1`，首页 CTA WXML 确认包含 `hover-class="none"`。

剩余风险 / 需要用户配合：

1. 真机联调如果仍 timeout，先确认后端不是只监听 `127.0.0.1`，需要用 `uvicorn pindou.main:app --host 0.0.0.0 --port 8000 --reload`；Windows 防火墙也可能需要允许 8000 入站。
2. 多机型适配已按运行时 API 实现，但仍建议用户在微信开发者工具里切 iPhone SE / iPhone 12-13 / iPhone 14 Pro Max 各点一次首页、上传页、作品页截图确认。
3. 当前使用微信原生 tabbar，不能直接给 tabbar 本身写 safe-area 样式；本次只保证页面正文内容不贴底。若未来改自定义 tabbar，需要复用同一套 `safeAreaBottom`。

## 2026-05-25 — Phase 2 frontend white screen / uid null fix

白屏连环崩溃已定位并修复，结论给用户 / Claude review：

1. `pages/generate/choice.vue` 和 `pages/error/error.vue` 的 dist 行号并不是指向 `image_id` / `variant` query 空值，而是指向 uni-app 编译出的内联 SVG 组件 props 调用。当前 alpha 版本在这些 SVG 虚拟组件路径里触发 `renderProps()`，`getCurrentInstance()` 偶发为 null，导致 `Cannot read property 'uid' of null`。
2. 已移除 `choice.vue`、`error.vue`、`MiniProgramLayout.vue` 里的内联 `<svg>/<path>/<circle>/<rect>`，改为 CSS 与文本符号渲染，避免再次走该编译路径。
3. `error.vue` 已从 `onMounted + getCurrentPages()` 改为 `onLoad(options)` 读取 `variant`，让错误兜底页即使在异常跳转链路里也不依赖 mounted 时机。
4. 验证：`npm run build:mp-weixin` 通过；`npm run dev:mp-weixin` 已重新生成 `dist/dev/mp-weixin`；三个现场文件的 dev dist 中不再出现 `resolveComponent("svg"/"path"/"circle")`，`choice.js` / `error.js` 仅保留 `MiniProgramLayout` 正常 props。
5. 剩余风险：项目其他页面若仍含内联 SVG，在 uni-app alpha 版本下可能遇到同类 `uid of null`。本次只处理报错现场和共用布局，若用户在其他页面看到同样堆栈，建议继续做一次全局 SVG 清扫。

需要用户操作：

1. 微信开发者工具里按 `Ctrl+R` 或点“编译”，重新跑：首页 → 上传 → 选择生成方式 → 错误页兜底。
2. 如果仍白屏，请截图 Console 第一条红字和页面路径；重点看是否已经换到其他页面的 dist 行号。

## 2026-05-25 — Phase 2 frontend generation result bugfix review

AI 路径 timeout、脚本 fallback 兔子占位图、标题实体转义、统计字段为 0 四个问题已处理，结论给用户 / Claude review：

1. Bug 1：`uni.uploadFile` 默认 60 秒不够覆盖 `gpt-image-2` 反代 30-60 秒耗时。已在 `generatePreview()` 和 `buildPattern()` 的两个上传请求里显式设置 `timeout: 120000`。
2. Bug 2：结果页显示兔子不是后端问题，而是 `pages/result/basic.vue` 对 quick / fallback 硬编码使用 `/static/assets/bead-bunny.svg`。已改为读取真实 `PatternSheet.grid` 并在结果页用 CSS grid 渲染拼豆预览；`artwork` store 会把最近一次真实 `PatternSheet` 写入 `pd_current_pattern`，避免跳转或热重载后回落到 mock。
3. Bug 3：标题前的 `&lt;` 来自返回箭头使用 HTML entity。已改为纯 CSS 箭头，不再渲染实体文本。
4. Bug 4：统计字段为 0 是因为结果页读旧字段 `total_beads / estimated_cost / colors`，后端实际返回 `bead_total / estimated_cost_cny / color_counts / palette_used`。已按 PRD §5.2 重新映射：总颗数、色号数、成本、色号清单均从真实后端字段计算。
5. 顺手降低同类白屏风险：`result/basic.vue` 内联 SVG 已替换为 CSS / 文本图标，避免再次触发 uni-app alpha 的 SVG `uid of null` 路径。
6. 验证：每个代码 commit 后均执行 `npm run build:mp-weixin`，最终 build 通过；`rg` 确认结果页不再含 `bead-bunny`、旧统计字段、`&lt;`、内联 SVG。

剩余风险 / 后续建议：

1. 当前结果页预览是前端根据 `PatternSheet.grid` 现场渲染，能解决“显示错图”和字段 0；但“保存图纸至相册”仍需要后端或前端导出真实 PNG 文件。现在若没有 `image_url`，会提示“图纸已生成，图片导出稍后开放”，不再误报下载失败。
2. 若产品要求立即保存图片，建议 task 后续补一个 `PatternExporter.to_simple_grid_png` 的 HTTP URL 返回，或在前端用 canvas 生成临时图片文件。
3. 项目其他页面仍可能残留内联 SVG。若后续又出现 `Cannot read property 'uid' of null`，优先 grep 报错页的 `<svg>/<path>/<circle>/<rect>` 并替换为 CSS/文本图标。

需要用户操作：

1. 微信开发者工具按 `Ctrl+R` 重新编译。
2. 用灰猫图重新走：上传 → 快速生成；预期结果页不再出现兔子，统计不再是 0。
3. 再走 AI 精品生成；若仍 timeout，请截图 Console 第一条红字和 Network 耗时。

## 2026-05-25 — Phase 2 frontend uploadFile error passthrough

用户截图显示 `Build pattern sheet error: Error: 图纸生成失败`，页面误跳“网络有点慢”。进一步排查结论：

1. 这次不是之前的 mock bunny 问题，而是 `api.buildPattern()` 的 `uni.uploadFile.success` 收到了非 2xx 响应后，把后端 `message_cn/error/statusCode` 全部吞掉，只抛固定 `Error("图纸生成失败")`。
2. 本地 SQLite 实测当前测试用户 `wx_e9b9d5ca2ea2d4ba1092c9d8` 的 `daily_quotas.script_used = 3`，正好达到 `SCRIPT_DAILY_FREE_LIMIT = 3`。因此截图这次大概率是后端返回 `429 QUOTA_EXCEEDED`，但前端误展示成网络慢。
3. 已新增 `PinDouApiError`：`preview/generate` 和 `pattern/build` 的 `uploadFile` 非 2xx 会解析 JSON body，透传 `statusCode`、`error`、`message_cn`、`details`。
4. `uploadFile.fail timeout` 现在统一转换为 `UPLOAD_TIMEOUT`，文案为“生成时间超过等待上限，请稍后重试。”，不会再裸露底层 errMsg。
5. `pages/preview/loading.vue` 已按错误码分流：`QUOTA_EXCEEDED` 跳 `variant=quota`，`CONSENT_REQUIRED` 跳授权提示，其余才作为生成失败 / 网络类错误。
6. `pages/error/error.vue` 支持 query 中的 `title` / `message`，后续错误页能展示真实后端中文原因。
7. 验证：`npm run build:mp-weixin` 通过。

需要用户操作：

1. 微信开发者工具按 `Ctrl+R` 重新编译后再测；如果本地额度仍是 3/3，预期现在会显示“今天的额度用完啦”，而不是“网络有点慢”。
2. 若要继续测试真实灰猫出图，需要重置本地开发库 `daily_quotas.script_used`，或临时增加每日脚本额度；不要在生产环境这样做。

## 2026-05-25 — Phase 2 product quality tuning review

对比小红书拼豆图纸参考后，本轮 5 个产品质量调优点已完成，结论给用户 / Claude review：

1. AI prompt 已从“照片转绘”收紧为“拼豆用 Q 版线稿”：强制儿童涂色书 / hand-drawn perler bead pattern 风格、3-5px 粗黑边、5-8 个纯色块，并加入 no fur texture / no realistic shading / no gradient / no anti-aliasing 等 negative 约束。
2. 默认尺寸已从偏密的大图转为 `40x40` Q 版小图；`60x80` / `80x100` / `100x120` 保留为更高阶预设。
3. 后端 PNG exporter 已新增带网格和色号 overlay 的导出能力：1x1 灰网格、10x10 红色大格、每格中心显示色号，底部 legend 输出 `code (count)`。
4. 结果页色卡 legend 已改为使用后端 `palette_used` 里的真实色号 + 中文名，不再显示英文 hex 名。
5. 结果页色号统计已改为行业更熟悉的格式：`色号 (数量 颗 · 中文色名)`，并按数量降序。

私有素材实测（文件均在 `01_research/tech/user_poc_private/`，不入 git）：

1. `incoming/kitten_gray_photo.png` 走 raw PatternBuilder `40x40`：输出 40x40、1600 颗、8 色；生成了 simple preview 和 labeled grid 两张私有验证图。
2. 同一张灰猫走调优后的 AI prompt：调用耗时约 56.3 秒，输出 40x40、1600 颗、7 色；主观观感明显更接近 Q 版拼豆，猫毛照片纹理已经被压掉很多。
3. before / after 摘要：before 更像照片量化或 mock 图，尺寸偏密、色号展示不专业；after 已变成 40x40 小图、低色数、可读网格、色号 + 中文名 legend。

剩余风险 / 建议下一步：

1. AI preview 目前仍可能返回白底 PNG 而不是 alpha 透明背景，导致白色背景被 PatternBuilder 计为真实豆子。建议下一个 micro-task 做“AI 预览白底自动转 NoBead”，或在 provider 后处理阶段强制把连通白底置 alpha。
2. 当前 MARD 数据库里的真实色号并不全部是 `M01` 这种格式，也会出现 `H2` / `R13` 等历史色号。前端已按后端真实 code 展示；如果产品侧要求统一成包装上的 `M01` 风格，需要 Task H/I 再补一层 canonical display code。
3. 带 overlay 的 PNG exporter 已有内部能力，但 API 还没有新增 labeled PNG URL 返回；本轮遵守“不新增 endpoint”，所以前端下载图纸仍需后续 task 接入。

验证记录：

1. `06_backend/.venv/Scripts/python.exe -m pytest tests/test_providers.py tests/test_pattern.py tests/test_api.py` 通过。
2. `05_frontend npm run build:mp-weixin` 通过。
3. 私有灰猫 raw / AI 两条链路均已生成验证图；验证图未纳入 git。

## 2026-05-25 — Phase 2 product quality tuning v2 review

对比真拼豆图纸 + 实物拼豆板后，本轮 v2 调优已完成，结论给用户 / Claude review：

1. 已新增 `01_research/colormap/pegboard_sizes.md` 和 ADR-010。调研结论：Hama/Perler/Artkal 常见国际 5mm 大方板更接近 `29×29`；本轮按用户实物反馈和国内 MVP 目标，默认采用国产 `26` 格板序列。
2. 尺寸预设已从视觉尺寸 `40×40 / 60×80 / 80×100 / 100×120` 改成物理板尺寸 `26×26 / 52×52 / 78×78 / 104×104`，默认 `26×26` 单板。
3. 前端生成方式页已增加四档尺寸选择：单板 / 双板 / 三板 / 四板，并把选择传给 loading → API。
4. PNG exporter 已把圆点改为带 1px 间距的圆角方块，更接近实际 5mm 方形拼豆颗粒。
5. labeled PNG 已增加拼豆板背景层：浅色板底、空心钉位、按 26 格推断的板边界线，再叠 1×1 灰网格和 10×10 红辅助线。
6. labeled PNG 每格提升到 22px，并放大格内色号与底部 legend，解决“看不太清楚”的问题。
7. AI Preview 已复用 `detect_and_remove_white_bg()` 做白底 flood-fill 去背景，配置开关为 `ENABLE_AI_PREVIEW_WHITE_BG_AUTO_NOBEED=true`。AI 路径去白底后再交给 PatternBuilder，避免白底误算成白豆。

私有灰猫实测（文件均在 `01_research/tech/user_poc_private/`，不入 git）：

1. raw 路径 `kitten_gray_photo.png` → `26×26`：676 颗 / 6 色，输出 `outgoing/kitten_gray_26x26_pegboard_labeled.png`。
2. AI 路径 `kitten_gray_photo.png` → `26×26`：反代耗时约 189 秒，`white_bg_detected=True`，输出 285 颗 / 7 色，输出 `outgoing/kitten_gray_ai_26x26_preview_stripped.png` 与 `outgoing/kitten_gray_ai_26x26_pegboard_labeled.png`。
3. before / after 摘要：before 是圆点/纯像素感、无物理板语义、白底会被算成豆；after 是方格豆、拼豆板底、26 板边界、字号更大、AI 白底变 NoBead。

验证记录：

1. `06_backend/.venv/Scripts/python.exe -m pytest tests/test_providers.py tests/test_pattern.py tests/test_api.py tests/test_models.py tests/test_services.py` 通过 28/28。
2. `05_frontend npm run build:mp-weixin` 通过。
3. `05_frontend npm run dev:mp-weixin` 已重新生成 dev 产物；`dist/dev/mp-weixin` 已确认包含 `26x26 / 52x52 / 78x78 / 104x104`。

剩余风险 / 建议下一步：

1. 国际品牌板（Hama / Perler / Artkal）常见是 `29×29`，而本轮默认是国产 `26` 格。Phase 3 若开放国际品牌，建议新增 `board_profile`，不要用同一套尺寸硬套所有品牌。
2. raw 脚本路径默认仍会保留照片背景并量化成豆，这符合“保留原图”的当前语义；若产品希望 raw 路径也能一键去白底，需要把 `auto_remove_white_bg` 暴露到前端。
3. `ENABLE_AI_PREVIEW_WHITE_BG_AUTO_NOBEED` 环境变量沿用了任务 prompt 的拼写 `NOBEED`。如果后续统一命名，可兼容新增 `NOBEAD` alias。

## 2026-05-26 — Phase 2 product quality tuning v3 review

本轮 v3 调优已完成，结论给用户 / Claude review：

1. “圆点改方格没生效”的根因不是后端 exporter，而是结果页主图没有用后端 PNG exporter，而是前端直接渲染 `PatternSheet.grid`，且 CSS 写了 `border-radius: 999px`。已把结果页主图改为方格豆，26/52 小尺寸逐格显示色号，78/104 大尺寸只在 10 格锚点显示色号，避免手机端糊成一片。
2. 后端 labeled PNG 也已复查并加固：26/52 尺寸用更大 cell 和更清晰字号，78/104 自动降低标注密度；方格半径收紧到 1px，视觉上不再接近圆点。
3. 已实现自定义画板尺寸：后端 `SizePreset` 支持 `30x30` / `45x45` 等字符串，校验范围为 20-200、长宽比 0.5-2、整数尺寸；非 26 倍数会在 `PatternSheet.metadata.warning` 返回“不对齐拼豆板”的提示，但仍允许生成。
4. 前端生成方式页已保留 26/52/78/104 四档推荐预设，并新增“自定义”输入区，实时显示绿色“对齐拼豆板”或黄色“不对齐”提示。
5. PRD §4.4 已新增 §4.4.2 自定义尺寸规则；ADR-010 已追加修订，明确推荐尺寸优先，但高级用户可自定义。
6. 作品集页面已从 stub 替换为真实实现：调用 `artworkStore.fetchArtworks()` / `api.getArtworks()`，两列作品网格、统计卡、空态 CTA、点开作品详情、长按或更多按钮弹分享 / 删除操作。
7. 我的页面已从 stub 替换为真实实现：调用 `userStore.fetchProfile()` / `api.getProfile()`，展示微信头像昵称、脚本 / AI / 月卡额度卡，以及我的作品、兑换 CDK、加客服微信、用户协议、关于入口。

验证记录：

1. `06_backend/.venv/Scripts/python.exe -m pytest` 通过 31/31。
2. `05_frontend npm run build:mp-weixin` 通过。
3. 本轮所有改动均未触碰 PRD §5 接口字段；私人素材目录未入 git。

需要用户操作：

1. 微信开发者工具按 `Ctrl+R` 重新编译后，重新生成一张 26×26 或 52×52 图纸，重点看主图是否已经是方格豆并显示色号。
2. 切到底部 tab 的“作品集”和“我的”，确认两个页面不再显示 Phase 2 占位文案。

## 2026-05-26 — Phase 2 product quality tuning v4 review

本轮 v4 调优已完成，结论给用户 / Claude review：

1. 结果页完整图纸改为两层展示：页面内只显示高清 PNG 缩略图 + 关键信息，点击主图或右上角“点击放大”按钮调用微信原生 `uni.previewImage()`，支持双指缩放、平移和保存到相册。
2. `result/basic.vue` 与 `result/premium.vue` 均已接入全屏预览；旧缓存没有 `metadata.labeled_image_url` 时仍保留前端 grid 兜底，不会白屏。
3. 后端生成 PatternSheet 时会保存带网格 / 色号的 PNG 到 `/static/patterns/`，并通过 `PatternSheet.metadata.labeled_image_url` 与可选 `image_url` 返回。`pattern/build` 同时保存 Artwork，让刚生成的作品也能进入作品集和分区查看。
4. 已实现分区图 API：`GET /api/v1/pattern/{artwork_id}/partitions`。默认 `partition_size=13`，`26×26` 拆 4 张，`52×52` 拆 16 张，更大尺寸继续按 13 格切分。
5. 分区图每张子图包含“第 N 区 / 共 M 区”、行列范围、全图位置缩略图、30px 单格和清晰色号。
6. 前端新增 `pages/result/partitions`：顶部全图缩略 + 当前区块高亮，主体 swiper 查看分区大图，底部上一/下一分页，并支持本地 `已拼完` 标记。
7. PRD §4.7 已新增 §4.7.1，落档“屏幕缩略 + 原生放大 + 分区查看”的实现规则。

验证记录：

1. `06_backend/.venv/Scripts/python.exe -m pytest` 通过 32/32。
2. `05_frontend npm run build:mp-weixin` 通过。
3. 当前分区图入口免费可见；月卡/高级版拦截还未接支付状态，后续可在 `pages/result/partitions` 加一层 `isMonthlyMember` 判断。

需要用户操作：

1. 重启/刷新后端后，在微信开发者工具按 `Ctrl+R`，重新生成一张图纸。
2. 点击结果页主图或“点击放大”，确认微信原生全屏预览可双指缩放。
3. 点击“分区查看”，用 `52×52` 重点验证是否拆成 16 张、每张 13×13 子图色号可读。

## 2026-05-26 — Phase 2 product quality tuning v4.1 bugfix review

本轮 v4.1 修复 2 个用户实测 bug：

1. `generate/choice.vue` 的 `&gt;` HTML 实体在小程序里不会自动解码，导致按钮显示“选这个 &gt;”。已全局 `rg "&gt;|&lt;|&amp;|&quot;" 05_frontend/src` 检查，残留只在生成方式页 3 处；已统一替换为 `›`，二次 grep 零命中。
2. 分区图色号重叠已修：`PatternExporter.render_partition_image()` 改为每个 cell 动态计算色号字体，公式为 `max(8, round(cell_px * 0.32))`，3 字符及以上色号再缩小 10%，并用等宽字体优先、每格左右保留 15% padding。
3. 分区图色号颜色仍按背景亮度自动黑 / 白；本次同时把分区图内嵌标题改成 ASCII 文案，避免服务器 Pillow 缺中文字体时出现方框乱码。

验证记录：

1. `05_frontend npm run build:mp-weixin` 通过。
2. `06_backend/.venv/Scripts/python.exe -m pytest tests/test_pattern.py` 通过 10/10；最终全量 pytest 也通过。
3. 私有灰猫 `user_poc_private/incoming/kitten_gray_photo.png` 已实测：`26×26` 拆 4 张，`52×52` 拆 16 张，样张输出到 `user_poc_private/outgoing/v4_1_partition_font/`（不入 git）。`52×52` 第 1 张分区图色号 H2/H14/H11 清晰、不重叠。

需要用户操作：

1. 微信开发者工具按 `Ctrl+R` 重新编译。
2. 重新走 AI / 快速生成到选择页，确认“选这个 ›”正常显示。
3. 重新生成图纸后进入分区查看，确认色号不再贴边或重叠。

## 2026-05-26 — Phase 2 product quality tuning v5 review

本轮 v5 按用户最新产品决策完成了分区交互简化：

1. 后端分区算法从“按 13×13 自动拆 N 张”改为固定 `2×2` 四象限，顺序固定为 `左上区 / 右上区 / 左下区 / 右下区`。
2. `/api/v1/pattern/{artwork_id}/partitions` 保留原有字段，并新增 `key`、`partition_layout=2x2`、`grid_offset`，方便前端画高亮区域；旧 `partition_size` 字段现在表示单个象限的最大边长。
3. `26×26 / 52×52 / 78×78 / 104×104` 均固定返回 4 张分区图，对应子图尺寸为 `13×13 / 26×26 / 39×39 / 52×52`。
4. `result/basic.vue` 和 `result/premium.vue` 已移除独立“点击放大”按钮，主图本身可点击调用 `uni.previewImage()`；首次显示轻量“轻点放大”提示，点击后本地记忆不再提示。
5. 主图旁分区入口文案统一为“📋 查看分区图”。
6. `pages/result/partitions.vue` 已从 swiper 翻页改为 2×2 象限网格，点击任意象限直接进入原生大图预览，可双指缩放。

验证记录：

1. `06_backend/.venv/Scripts/python.exe -m pytest` 通过 33/33。
2. `05_frontend npm run build:mp-weixin` 通过。
3. 私有灰猫 `user_poc_private/incoming/kitten_gray_photo.png` 已实测 `26×26 / 52×52 / 78×78 / 104×104`，均返回 4 张分区图；样张输出到 `user_poc_private/outgoing/v5_2x2_partitions/`（不入 git）。

需要用户操作：

1. 微信开发者工具按 `Ctrl+R` 重新编译。
2. 重新生成一张 `52×52` 或 `78×78` 图纸，确认结果页主图可直接点击放大。
3. 点击“📋 查看分区图”，确认页面只显示四个象限卡片，任意卡片点击后可全屏缩放查看。

## 2026-05-26 — Phase 2 v8.5 Hupijiao payment handoff

虎皮椒支付码方案已按 ADR-011 接入，开发期可无真实账号跑通 UI 和 webhook：

1. 后端已实现虎皮椒下单 / 查单 / webhook 验签；未配置真实虎皮椒密钥时返回本地 placeholder 二维码。
2. 前端 Paywall 已改为默认展示“虎皮椒微信支付”二维码，每 3 秒轮询订单状态；“换种付款方式”会创建客服扫码兜底订单。
3. 开发期可用 `python scripts/mock_hupijiao_webhook.py <order_no> --amount 28.00` 模拟支付成功。金额必须与订单 SKU 一致：单次 9.90，月卡 28.00，人工精修 99.00。
4. 上线前请用户提供并只写入生产 `.env`：`HUPIJIAO_APP_ID`、`HUPIJIAO_APP_SECRET`、`HUPIJIAO_WEBHOOK_SECRET`。
5. 上线前需要在虎皮椒后台配置 webhook URL：`https://api.pindou.cn/api/v1/webhook/hupijiao`，并确认虎皮椒当前是否支持个人主体注册和稳定收款。
6. 我从 `Desktop/apisell` 只复用了虎皮椒签名 / 参数 / 回调处理模式，没有复制任何密钥；发现的旧 `github-research` skill 当前 Codex 已有同等能力，未重复搬运。

## 2026-05-27 — Phase 2 wxcloud migration handoff

本轮已按 ADR-012 把 PinDou MVP 部署主路线迁到微信云托管：

1. 后端已 Docker 化，云托管容器入口为 `uvicorn pindou.main:app --host 0.0.0.0 --port 8000`。
2. 数据库支持 `DATABASE_URL` 双模式：本地默认 SQLite，生产用 `mysql+pymysql://...` 云托管 MySQL。
3. 文件存储已抽象为 `StorageBackend`：本地开发走 `local`，生产走腾讯云 COS。
4. 前端默认走 `wx.cloud.callContainer`，小程序图片上传从 `uni.uploadFile` 改成 base64 JSON；本地 HTTP fallback 仍可用。
5. 虎皮椒 webhook URL 改为云托管默认 HTTPS 域名下的 `/api/v1/webhook/hupijiao`。
6. 旧上海机 + Nginx + systemd 部署文档已保留到 `07_ops/deployment_legacy.md`，作为回退方案。

### 部署到微信云托管步骤（用户做）

1. 微信公众平台 → 开通“微信云托管”（需要小程序管理员）。
2. 创建环境（推荐上海地域）→ 记录 env ID。
3. 创建云托管服务，服务名建议 `pindou-backend`。
4. 创建 MySQL 数据库实例 → 拿到连接信息，拼出 `DATABASE_URL`。
5. 创建 COS bucket → 拿到 `COS_SECRET_ID` / `COS_SECRET_KEY` / `COS_BUCKET` / `COS_REGION`。
6. 云托管环境变量页配置 `.env.example` 中全部生产变量：虎皮椒密钥、反代密钥、`DATABASE_URL`、COS 信息、JWT、微信 AppSecret 等。
7. 关联 GitHub repo 或上传 Docker 镜像，部署后确认 `/health` 返回 `{"status":"ok"}`。
8. 在云托管环境执行 `alembic upgrade head` 初始化 MySQL。
9. 如已有本地 SQLite 数据，跑 `06_backend/scripts/sqlite_to_mysql.py` 做一次迁移。
10. 拿到云托管 HTTPS URL 后，到虎皮椒后台把 webhook 改为 `https://<云托管默认域名>/api/v1/webhook/hupijiao`。
11. 前端配置 `VITE_WX_CLOUD_ENV=<env ID>`、`VITE_WX_CLOUD_SERVICE=pindou-backend` 后重新编译小程序。
12. 真机完整回归：登录 / 同意协议 / 上传 / 快速生成 / AI 精品 / 作品集 / 支付二维码 / mock 或真实 webhook。

### 需要用户准备 / 确认

1. 微信云托管 env ID 和 service name。
2. 云托管 MySQL 连接串。
3. COS bucket 与密钥。
4. 虎皮椒生产密钥与后台 webhook URL 配置。
5. 是否保留当前上海机作为临时 fallback；如果保留，只做备份，不再作为 MVP 主路径。

### 本地回归结果

1. 后端全量测试：`06_backend/.venv/Scripts/python.exe -m pytest` 通过 `42 passed`。
2. Alembic 本地 SQLite 验证：临时 `sqlite:///./var/wxcloud_regression.db` 执行 `alembic upgrade head` 成功。
3. 前端小程序构建：`05_frontend npm run build:mp-weixin` 成功。
4. Docker 本地验证未执行：当前 Windows 环境没有安装 `docker` CLI，需在已安装 Docker Desktop 或云托管构建环境验证 `docker build -t pindou-backend .`。
5. MySQL / COS / `wx.cloud.callContainer` 真实链路仍需上微信云托管后验证；本地已保留 `VITE_USE_WX_CLOUD=false` 和传统 HTTP fallback 方便排错。

## 2026-05-28 — Phase 2 wxcloud CDK / Hupijiao P0 handoff

本轮处理两个真机 P0 问题：

1. CDK “没有找到相关资源”的根因是云托管数据库缺测试 CDK 数据。已在云端临时生成 3 个 `monthly_card` 测试 CDK，兑换码只在本次对话里给用户，不写入 git；后续可用 `06_backend/scripts/seed_test_cdks.py` 通过 admin API 生成新测试码。
2. 发现云托管环境的 `JWT_SECRET` 仍可能使用默认开发值或未配置。上线前必须在微信云托管服务设置里配置强随机 `JWT_SECRET`，并配置 `ADMIN_USERNAME` + `ADMIN_PASSWORD_HASH`，然后重新部署；否则 admin token 有被伪造风险。
3. 虎皮椒下单在云端实测已返回真实 `api.xunhupay.com` 二维码地址，`is_mock_payment=False`。真机仍显示 PD placeholder 的主要风险是小程序 `<image>` 加载外部 `api.xunhupay.com` 域名失败，或 Paywall 的 PD overlay 造成误判。
4. 已改为后端代理虎皮椒二维码：前端加载 `https://<云托管服务>/api/v1/payment/order/{order_no}/qr.png`，后端再去拉虎皮椒原始二维码，避开小程序外部图片域名限制。
5. 已给 `hupijiao_service.py` 增加脱敏日志：调用前记录不含签名/密钥的 payload，调用后记录 status/body，异常时写完整 stack trace。若仍出现 placeholder，请先查云托管“运行日志”里的 `Hupijiao` 关键字。

需要用户 / Claude 做：

1. 把云托管服务设置里的最小实例数改为 `1`（当前 0 会 30 分钟无请求自动暂停，真机首次请求容易慢/失败；确认成本后再评估是否改回）。
2. 设置生产安全环境变量：`JWT_SECRET`、`ADMIN_USERNAME`、`ADMIN_PASSWORD_HASH`。
3. 确认虎皮椒后台 webhook URL 已改为：`https://pindou-backend-263102-4-1437642655.sh.run.tcloudbase.com/api/v1/webhook/hupijiao`。
