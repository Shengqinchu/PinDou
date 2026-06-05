# PinDou 微信云托管部署运维文档

> **目标环境**：微信云托管（上海地域优先）  
> **状态**：Phase 2 已迁移为 Docker + MySQL + COS + `wx.cloud.callContainer` 主路径  
> **旧部署 fallback**：见 `07_ops/deployment_legacy.md`

---

## 0. 当前 Web 域名

- 正式入口：`https://pindoupuppy.com/`
- 同源 API：`https://pindoupuppy.com/api/v1`
- 管理后台：`https://pindoupuppy.com/Ios235169`
- 健康检查：`https://pindoupuppy.com/health`
- 对外验收、用户链接、截图和文档统一使用主域。旧 staging 子域仅保留为临时兼容/回滚入口，不再作为正式入口。
- Cloudflare 当前路由（2026-06-05 已切）：`pindoupuppy.com` 和 `staging.pindoupuppy.com` 均 CNAME 到同一条 Cloudflare Tunnel（`pindou-staging`），Tunnel ingress 覆盖 `pindoupuppy.com` / `www.pindoupuppy.com` / 旧 staging 子域，源站为 `https://localhost`（`noTLSVerify=true`）。
- 旧 Worker routes `pindoupuppy.com/*`、`www.pindoupuppy.com/*`（脚本 `pindoupuppy-origin-proxy`）曾强制跳 `/h5/`，已删除；不要重新启用。若再次看到 `/` 跳到 `/h5/` 或 `/health` 为边缘 404，优先检查是否误恢复了这些 Worker routes 或把主域 DNS 指回腾讯云托管后端。

---

## 1. 架构

```text
[微信小程序]
    |
    | wx.cloud.callContainer
    v
[微信云托管 FastAPI Docker]
    |
    | SQLAlchemy / Alembic
    v
[云托管 MySQL]
    |
    | StorageBackend
    v
[腾讯云 COS]
    |
    | payment/create + webhook
    v
[虎皮椒]
```

### 1.1 关键差异

| 项目 | 传统部署 | 云托管部署 |
| --- | --- | --- |
| 小程序访问 | `https://api.pindou.cn/api/v1` | `wx.cloud.callContainer` |
| 域名 / ICP | 需要自有域名备案 | MVP 期使用微信云托管默认域名 |
| 运行方式 | systemd + Uvicorn + Nginx | Docker 容器 |
| 数据库 | SQLite / 未来 PG | 云托管 MySQL |
| 文件存储 | 本地 `var/` | 腾讯云 COS |
| webhook | 自有域名 | 云托管 HTTPS 域名 |

---

## 2. 后端容器

后端目录：`06_backend/`

### 2.1 本地构建

```bash
cd 06_backend
docker build -t pindou-backend .
docker run --rm -p 8000:8000 --env-file .env pindou-backend
curl http://localhost:8000/health
```

预期返回：

```json
{"status":"ok"}
```

### 2.2 Dockerfile

当前容器入口为：

```bash
uvicorn pindou.main:app --host 0.0.0.0 --port 8000
```

云托管部署时只需要暴露容器端口 `8000`。

---

## 3. 环境变量

生产环境变量在微信云托管控制台配置，严禁写入 git。

### 3.1 必填

| 变量 | 说明 |
| --- | --- |
| `APP_ENV=production` | 生产模式 |
| `DATABASE_URL` | 云托管 MySQL 连接串，格式见 `.env.example` |
| `STORAGE_BACKEND=cos` | 生产使用 COS |
| `COS_SECRET_ID` / `COS_SECRET_KEY` | COS 密钥 |
| `COS_BUCKET` / `COS_REGION` | COS bucket 与地域 |
| `JWT_SECRET` | JWT 签名密钥 |
| `WECHAT_MP_APPID` / `WECHAT_MP_APPSECRET` | 小程序登录 |
| `XIAOCHI_GPT_API_KEY` | AI 反代调用 |
| `HUPIJIAO_APP_ID` / `HUPIJIAO_APP_SECRET` / `HUPIJIAO_WEBHOOK_SECRET` | 虎皮椒 |
| `HUPIJIAO_CALLBACK_URL` | 云托管 HTTPS URL + `/api/v1/webhook/hupijiao` |

### 3.2 推荐

| 变量 | 推荐值 |
| --- | --- |
| `APP_CORS_ALLOW_ORIGINS` | 云托管私有协议为主，保留本地调试域 |
| `COS_PUBLIC_BASE_URL` | 如开 CDN 或自定义访问域则填写 |
| `ENABLE_REVERSE_PROXY_HEALTH_MONITOR` | `true` |
| `ENABLE_EXPIRED_ORIGINAL_DELETE_TASK` | `true` |

---

## 4. 数据库

### 4.1 MySQL 初始化

1. 微信云托管控制台创建 MySQL。
2. 创建数据库 `pindou`，字符集建议 `utf8mb4`。
3. 配置 `DATABASE_URL=mysql+pymysql://user:password@host:3306/pindou?charset=utf8mb4`。
4. 容器启动后执行 Alembic：

```bash
cd 06_backend
alembic upgrade head
```

### 4.2 SQLite 迁移到 MySQL

如本地已有 SQLite 数据：

```bash
cd 06_backend
python scripts/sqlite_to_mysql.py \
  --sqlite sqlite:///./var/pindou.db \
  --mysql "mysql+pymysql://user:password@host:3306/pindou?charset=utf8mb4" \
  --dry-run

python scripts/sqlite_to_mysql.py \
  --sqlite sqlite:///./var/pindou.db \
  --mysql "mysql+pymysql://user:password@host:3306/pindou?charset=utf8mb4"
```

先跑 `--dry-run` 看行数，再执行真实迁移。

---

## 5. COS 存储

### 5.1 创建 bucket

1. 腾讯云 COS 创建 bucket，地域建议与云托管一致（上海）。
2. 配置最小权限密钥，只允许当前 bucket 的对象读写删除。
3. 环境变量设置：

```env
STORAGE_BACKEND=cos
COS_SECRET_ID=...
COS_SECRET_KEY=...
COS_BUCKET=...
COS_REGION=ap-shanghai
COS_PUBLIC_BASE_URL=
```

### 5.2 路径约定

| 类型 | key 前缀 |
| --- | --- |
| 用户原图 | `uploads/` |
| AI preview | `previews/` |
| 图纸 PNG / JSON | `patterns/` |
| 缩略图 | `thumbnails/` |

ADR-009 仍然生效：用户原图 30 天后删除，PatternSheet 和成品图保留。

---

## 6. 前端云托管配置

前端目录：`05_frontend/`

### 6.1 环境变量

```env
VITE_USE_WX_CLOUD=true
VITE_WX_CLOUD_ENV=<微信云托管环境 ID>
VITE_WX_CLOUD_SERVICE=pindou-backend
VITE_WX_CLOUD_API_PREFIX=/api/v1
```

本地联调老 HTTP 路径时可临时设置：

```env
VITE_USE_WX_CLOUD=false
VITE_PINDOU_DEV_API=http://192.168.2.40:8000/api/v1
```

### 6.2 图片上传

云托管路径不再使用 `uni.uploadFile`。前端读取本地图片为 base64，通过 JSON 发送：

- AI preview：`POST /api/v1/preview/generate`
- 脚本图纸：`POST /api/v1/pattern/build`

后端负责 base64 解码、格式校验和存储抽象落盘 / 上传 COS。

---

## 7. 虎皮椒 webhook

部署成功后，从微信云托管控制台复制默认 HTTPS URL，并在虎皮椒后台设置：

```text
https://<云托管默认域名>/api/v1/webhook/hupijiao
```

同步更新生产环境变量：

```env
HUPIJIAO_CALLBACK_URL=https://<云托管默认域名>/api/v1/webhook/hupijiao
```

开发期可继续用：

```bash
cd 06_backend
python scripts/mock_hupijiao_webhook.py <order_no> --amount 28.00
```

---

## 8. 部署步骤（用户执行）

1. 微信公众平台开通“微信云托管”。
2. 创建环境，推荐上海地域，记录 env ID。
3. 创建云托管服务，服务名建议 `pindou-backend`。
4. 创建 MySQL，并配置 `DATABASE_URL`。
5. 创建 COS bucket，并配置 `STORAGE_BACKEND=cos` 与 COS 密钥。
6. 在云托管服务环境变量页录入 `.env.example` 中的生产变量。
7. 关联 GitHub repo 或上传 Docker 镜像。
8. 部署后访问 `/health`，确认返回 `{"status":"ok"}`。
9. 执行 `alembic upgrade head` 初始化 MySQL 表。
10. 如已有 SQLite 数据，执行 `scripts/sqlite_to_mysql.py` 迁移。
11. 修改虎皮椒后台 webhook URL。
12. 前端配置 `VITE_WX_CLOUD_ENV` 后重新编译小程序，真机测试登录、上传、生成、支付和作品集。

---

## 9. 监控与回退

### 9.1 云托管监控

- 容器启动失败 / 重启次数
- API 错误率和 P95 延迟
- MySQL 连接数与慢查询
- COS 读写失败率
- 虎皮椒 webhook 验签失败率
- 反代健康检查失败次数（ADR-007）

### 9.2 回退条件

见 ADR-012：

1. 云托管月成本连续 2 个月超过 200 元且高于传统部署。
2. 云托管限流、冷启动或不可用影响生成链路。
3. 用户量超过 5 万，需要重新核算资源和架构。

触发后恢复 `deployment_legacy.md` 的传统服务器路径，或拆分为小程序云托管 + 独立后端混合部署。
