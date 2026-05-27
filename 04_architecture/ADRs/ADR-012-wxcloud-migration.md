# ADR-012: 微信云托管迁移

- **状态**: Accepted（2026-05-27）
- **日期**: 2026-05-27
- **决策者**: 用户 + Codex
- **影响范围**: 部署架构、前端通信、数据库、对象存储、虎皮椒 webhook、运维文档

## 背景

Phase 2 原部署路线是备案 `.cn` 域名、上海云服务器、Nginx、systemd、Let's Encrypt。该路线需要 ICP 备案和域名配置，预计上线前置周期约 18-25 天。

用户调研微信云托管后决定改用云托管 Docker 部署。小程序通过 `wx.cloud.callContainer` 访问容器服务，使用微信私有协议与云托管默认 HTTPS 域名，MVP 期跳过自有域名备案和 Nginx 反代。

## 决策

PinDou MVP 期使用微信云托管替代传统服务器部署：

```text
小程序前端
  -> wx.cloud.callContainer
微信云托管 FastAPI Docker
  -> 云托管 MySQL
  -> 腾讯云 COS
  -> 虎皮椒支付 API / webhook
```

传统上海机部署文档保留为 `07_ops/deployment_legacy.md`，作为云托管成本或限流不可接受时的回退路径。

## 实现影响

1. 后端使用 `06_backend/Dockerfile` 构建 FastAPI 容器。
2. `DATABASE_URL` 支持 SQLite 开发模式与 MySQL 生产模式。
3. 存储层通过 `StorageBackend` 抽象在本地磁盘和腾讯云 COS 之间切换。
4. 前端默认使用 `wx.cloud.callContainer`，通过 `VITE_WX_CLOUD_ENV`、`VITE_WX_CLOUD_SERVICE` 和 `VITE_WX_CLOUD_API_PREFIX` 配置目标环境；传统 HTTP 保留为 fallback。
5. 图片上传从 `uni.uploadFile` multipart 改为 base64 JSON，后端在 API 层解码并复用原有上传规范化流程。
6. 虎皮椒 webhook URL 改为云托管默认 HTTPS 域名下的 `/api/v1/webhook/hupijiao`。

## 回退触发条件

出现以下任一情况，重新评估是否回到传统部署或混合部署：

1. 云托管月成本连续 2 个月超过 200 元，且高于传统服务器 + 对象存储方案。
2. 云托管限流、冷启动或服务不可用影响核心生成链路。
3. 小程序用户量超过 5 万，云托管的流量、日志、数据库或对象存储成本结构需要重新核算。

## 后果

### 正面

- MVP 上线周期从备案驱动改为云托管配置驱动。
- 小程序端免配置自有服务器域名，减少审核前置工作。
- MySQL 和 COS 成为默认生产持久化方案，规避本地磁盘容量风险。

### 代价

- 前端调用路径与本地调试路径分叉，需要保留 `USE_WX_CLOUD=false` fallback。
- 图片 base64 JSON 会增加请求体积，后续如遇限额需要切到云存储 fileID 上传方案。
- 运维依赖微信云托管控制台、环境变量和默认域名配置，传统 SSH 运维能力不再覆盖全部问题。

## 关联

- ADR-006：个人主体策略不变，官方微信支付长期路径仍需主体升级。
- ADR-007：反代模型风险不变；云托管只解决小程序访问域名与后端托管问题。
- ADR-009：私人素材不入 git，云托管 COS 生产存储仍需按 30 天删除原图。
- ADR-011：虎皮椒支付码方案继续使用，webhook URL 改为云托管域名。
- FUTURE_WORK #2 / #3 / #6：跨境合规、对象存储和主体升级的触发条件已随本 ADR 更新。
