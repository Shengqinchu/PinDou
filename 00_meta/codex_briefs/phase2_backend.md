# Codex Phase 2 后端 Brief

**Status**: in_progress (Codex @ 2026-05-25) — task 5 API endpoints done, waiting Claude review
**Owner**: Codex
**Priority**: P0
**Estimated**: 3-4 周（含 8 个子任务）
**前置**: Phase 1 PRD v1.0 已冻结（`02_product/PRD_v1.0.md`）

---

## 前置阅读（必读）

按顺序读：
1. `02_product/PRD_v1.0.md`（**实施合同，按这个写代码**）
2. `04_architecture/ADRs/`（全部 10 个 ADR，特别 003 / 005a / 006 / 007 / 008 / 009）
3. `00_meta/FUTURE_WORK.md`（影响实现边界）
4. `00_meta/api_inventory.md`（反代 API + 模型清单）
5. `07_ops/deployment.md`（部署架构 + P0 安全 TODO）
6. `01_research/tech/perler_bead_domain_notes.md`（拼豆领域知识，PatternBuilder 必须遵守）
7. `01_research/tech/algorithms.md` + `algorithm_impls/`（Task B 推荐：K-means + CIEDE2000 + 无抖动）
8. `01_research/tech/poc_runner.py`（PreviewProvider P1 调用参考）
9. `01_research/colormap/` + `01_research/colormap_china/`（色卡数据库）

---

## 技术栈（已定）

- **语言**：Python 3.11+
- **框架**：FastAPI + Uvicorn
- **DB**：SQLite（MVP）→ PostgreSQL（1 万用户后切换，Phase 5+）
- **算法**：Pillow + numpy + scikit-learn + colormath
- **AI Provider**：openai SDK 调反代 `gpt-image-2`
- **部署**：systemd + Nginx + Let's Encrypt（详见 `07_ops/deployment.md`）

---

## 任务分解（8 个子任务）

### 任务 0：SSH 进服务器查硬件 + 填 deployment.md（最先做）

**SSH 凭证**：从本地 `.env` 读 `PINDOU_PROD_SSH_*`。2026-09-18 起目标为 `36.139.201.94`，使用新 Ed25519 key；详见 `07_ops/SERVER_ASSETS.md`，密码及私钥不写到 commit。

**要查的信息**：
```bash
ssh pindou-prod
# 上去后执行：
df -h                          # 硬盘
lsblk                          # 块设备
free -h                        # 内存
nproc                          # CPU 核数
cat /proc/cpuinfo | head -25   # CPU 型号
uname -a                       # 内核 / 版本
lsb_release -a                 # 发行版
ip addr                        # 网络接口
ss -tulpn                      # 已开端口
which python3 python3.11       # Python 现状
which nginx                    # Nginx 现状
df -h /var                     # /var 分区（用户数据存这）
```

**输出**：填入 `07_ops/deployment.md` §1.1 表格 + §4 软件栈"已安装"列。

**如果硬盘 < 100 GB**：在 `_questions_for_user.md` 提醒用户"建议立即接对象存储或扩容"。
**如果硬盘 ≥ 200 GB**：MVP 期本地存够用，关闭 FUTURE_WORK 第 3 条触发条件之一。

**完成后立刻执行 deployment.md §2 的 3 项 P0 安全 TODO**（改 SSH key / 创 pindou 用户 / 防火墙）。

### 任务 1：项目结构 + 依赖管理

```
06_backend/
├── pyproject.toml             # poetry / pip-tools
├── requirements.txt
├── .env.example               # 从根目录 .env.example 同步
├── pindou/
│   ├── __init__.py
│   ├── main.py                # FastAPI app
│   ├── config.py              # 配置 + .env 加载
│   ├── api/                   # API 端点
│   │   ├── __init__.py
│   │   ├── upload.py
│   │   ├── generate.py
│   │   ├── pattern.py
│   │   ├── artwork.py
│   │   ├── user.py
│   │   ├── payment.py
│   │   ├── cdk.py
│   │   └── admin.py
│   ├── providers/             # PreviewProvider（ADR-008）
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── xiaochi_gpt.py     # P1 反代实现
│   │   └── fallback_quantize.py  # 兜底：直接量化
│   ├── pattern/               # PatternBuilder（ADR-008）
│   │   ├── __init__.py
│   │   ├── builder.py
│   │   ├── quantize.py        # K-means + CIEDE2000（复用 Task B 实现）
│   │   ├── postprocess.py     # 去孤点 / 黑边保护 / 透明背景
│   │   └── exporter.py        # PNG / PDF / Excel / 分区图
│   ├── colormap/              # 色卡 / SKU 数据访问
│   │   ├── __init__.py
│   │   ├── loader.py
│   │   └── matcher.py
│   ├── db/                    # 数据模型
│   │   ├── __init__.py
│   │   ├── models.py          # SQLAlchemy
│   │   └── migrations/
│   ├── services/              # 业务逻辑
│   │   ├── __init__.py
│   │   ├── user_service.py
│   │   ├── artwork_service.py
│   │   ├── cdk_service.py
│   │   └── payment_service.py
│   └── tasks/                 # 定时任务
│       ├── delete_expired_originals.py  # ADR-009 30 天后删原图
│       └── reverse_proxy_health_check.py  # 反代健康检查
└── tests/
```

### 任务 2：PreviewProvider 实现（PRD §5.1）

按 PRD §5.1 接口契约：
- `xiaochi_gpt.XiaochiGptProvider`：调反代 `gpt-image-2`，按 PRD §4.3 四个风格预设构 prompt（来源 `01_research/tech/prompts.md` + 拼豆约束）
- `fallback_quantize.FallbackProvider`：调 `PatternBuilder.build(raw_image)` 返回脚本量化输出当 Preview
- Fallback chain：主 → fallback（ADR-005 fallback chain）

**重试 / 超时**：
- 单次调用 90 秒超时
- 失败重试 1 次（同 provider 不同 seed）
- 再失败 → fallback

### 任务 3：PatternBuilder 实现（PRD §5.2）

按 PRD §5.2 接口契约（支持 `preview` / `raw_image` 两种输入）：
- 算法基线：复用 `01_research/tech/algorithm_impls/` 的 K-means + CIEDE2000 + 无抖动
- 拼豆后处理：
  - 去孤点（小于 N 像素的色块合并到邻居）
  - 黑边保护（不让黑色被合并）
  - 透明背景识别（alpha < 0.5 → NoBead）
- 输出 `PatternSheet` 完整结构（grid / counts / cost / palette_used）

**测试**：用 Task B 的 3 张测试图（synthetic）做回归测试，结果应与 `algorithm_metrics.csv` 一致。

### 任务 4：数据模型（PRD §6）

按 PRD §6 数据模型：
- `User` / `Artwork` / `Order` / `CDK`
- SQLAlchemy ORM
- Alembic migrations
- SQLite 本地开发，PG 生产候选（配置驱动）

### 任务 5：API 端点

按 PRD §3 用户路径 + §4 功能清单，每个端点对应一个用户路径节点：
- `POST /api/upload` — 上传图
- `POST /api/generate/script` — 脚本快速生成（PRD §4.5）
- `POST /api/generate/ai` — AI 精品生成（PRD §4.6）
- `POST /api/pattern/build` — PatternBuilder（PRD §4.7）
- `GET/POST/DELETE /api/artwork/*` — 用户作品集（PRD §4.10）
- `POST /api/payment/order` — 创建订单（加客服扫码付）
- `POST /api/cdk/redeem` — CDK 兑换（PRD §4.9）
- `GET /api/user/me` — 用户信息 + 额度

每个端点必须有：
- 输入验证（pydantic）
- 错误码（统一字典）
- 鉴权（微信 openid → JWT）
- 频率限制（CDK 兑换接口尤其严，PRD §6.5 安全设计）

### 任务 6：CDK 系统（PRD §4.9 + §6.5）

- 后台批量生成接口（18 位安全字典字符串，无 I/O/0/1）
- 兑换接口 + 防滥用（IP + 用户级频率限制）
- 管理面板（最小可用）：列表 / 生成 / 状态 / 销售渠道标记

### 任务 7：管理后台 + 客服面板（最小可用）

- 订单列表 + 手动确认（"加客服扫码付"流程要客服手动开通额度）
- CDK 管理
- 用户列表 + 额度调整
- 简单鉴权（用户名 + 密码 hash）

### 任务 8：部署上线

按 `07_ops/deployment.md` §5 部署流程：
- 配置 systemd
- 配置 Nginx（HTTPS 等域名备案后）
- 启动监控
- 完成 deployment.md 的所有空字段填充

---

## 必须遵守

### 1. 不写 API key
所有 key 走 `.env`（已 gitignore），代码用 `os.getenv()` 读。`.env.example` 列变量名不列值。

### 2. 私人素材规则（ADR-009 hard rule）
- 用户上传原图：本地短期存储（生成完即可删 AI 中间产物），30 天后**定时任务**删原图
- 不入 git
- 测试用 `01_research/tech/test_inputs/` 的合成图

### 3. 接口契约不可改
PRD §5 接口签名（PreviewProvider / PatternBuilder）冻结。新增字段允许，改名 / 删字段必须开 ADR 通知所有依赖方（包括 Gemini 前端）。

### 4. 反代风险监控（ADR-007）
任务 0 部署后必须实现反代健康检查（每 5 min ping `/v1/models`），故障 > 6 小时告警。

### 5. Commit 规范
- 分支：`phase2`（已存在）
- 子任务完成后 commit：`feat(backend-taskN): 描述` 或 `chore(deploy): 描述`
- 每完成一个任务在 `_questions_for_user.md` 加阶段汇报

### 6. 评审节点
- 任务 0 / 1 完成后：用户 review（确认硬件 + 项目结构）
- 任务 2 / 3 完成后：用户 review（核心算法可用性）
- 任务 5 完成后：用户 review（API 可用性）
- 任务 8 完成后：用户 review（上线就绪）

---

## 接口契约对接 Gemini 前端

前端 brief 在 `00_meta/gemini_briefs/phase2_frontend_design.md`。后端 + 前端共享：
- PRD §5 API 端点（前端调用）
- PRD §6 数据模型（前端展示）
- PRD §3 用户路径（前后端协作流程）

任何接口字段改动必须**先在 `_questions_for_user.md` 提出 + 同步通知 Gemini**。
