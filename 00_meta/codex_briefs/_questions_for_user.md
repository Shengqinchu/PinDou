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
