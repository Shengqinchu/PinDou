# ADR-011: 虎皮椒微信支付码方案

- **状态**: Accepted（2026-05-26）
- **日期**: 2026-05-25
- **修订日期**: 2026-05-26
- **决策者**: 用户 + Claude Code PM review + Codex implementation review
- **影响范围**: 变现路径自动化、Paywall、订单状态机、webhook 验签、PRD §4.8

## 决策

Phase 2 接入虎皮椒支付码方案，但不走 H5 跳转。

小程序内展示虎皮椒生成的微信支付二维码，用户长按识别付款。支付成功后，虎皮椒 webhook 通知后端；后端验签、校验金额、幂等更新订单状态并发放权益。客服扫码继续作为兜底入口。

## 用户路径

1. 用户在 Paywall 选择单次、月卡或人工精修。
2. 前端调用 `POST /api/v1/payment/order/create`，只传 `sku`，金额由后端 SKU 表决定。
3. 后端创建本地订单，调用虎皮椒 `/payment/do.html`，返回 `qr_code_url`、`order_no`、`expires_at`。
4. 小程序内显示二维码与“长按识别付款”提示，并每 3 秒轮询订单状态。
5. 虎皮椒回调 `POST /api/v1/webhook/hupijiao`。
6. 后端按虎皮椒签名规则验签，校验金额，`pending_qr -> paid_via_hupijiao`，然后发放单次额度或延长月卡。
7. 前端轮询到 `paid_confirmed` 后关闭 Paywall，刷新用户额度并跳转作品集。

## 为什么不走 H5 跳转

- H5 跳转需要独立域名、备案和回跳小程序处理，体验割裂。
- 支付码方案不离开小程序；用户只需要长按二维码识别。
- 与当前 Paywall UI 兼容，改造成本低。

## 实现要点

### 后端

- `pindou/services/hupijiao_service.py` 封装下单、查单、签名和验签。
- `POST /api/v1/payment/order/create` 默认创建虎皮椒二维码订单。
- `POST /api/v1/payment/customer-service/order/create` 保留客服扫码兜底订单。
- `POST /api/v1/webhook/hupijiao` 接收回调，只在验签和金额校验通过后处理。
- 订单新增 `payment_provider`，取值为 `hupijiao` 或 `customer_service`。
- 订单状态扩展为 `pending_qr -> paid_via_hupijiao`。

### 前端

- `Paywall.vue` 从“套餐选择”切到“虎皮椒微信支付”二维码页。
- 每 3 秒轮询 `/payment/order/{order_id}`，最多 5 分钟。
- 支付成功后刷新用户资料，关闭 Paywall 并跳作品集。
- 提供“换种付款方式”，创建客服扫码兜底订单。

### 开发测试

- 未配置虎皮椒密钥时，后端返回本地 placeholder 二维码，便于跑通 UI。
- `scripts/mock_hupijiao_webhook.py` 可模拟 `OD` 支付成功回调。
- 开发环境如未配置 webhook secret，使用固定开发 mock secret；生产必须配置真实 `HUPIJIAO_WEBHOOK_SECRET`。

## 安全约束

- `HUPIJIAO_APP_SECRET` 和 `HUPIJIAO_WEBHOOK_SECRET` 只允许存在于 `.env`，不得入 git。
- webhook 必须验签；验签失败返回 `fail`。
- 金额必须以本地订单金额为准，前端不能传金额。
- 同一订单已支付时重复回调只返回 `success`，不重复发放权益。
- 客服扫码只作为兜底，不覆盖虎皮椒主路径。

## 风险

- 虎皮椒平台可用性和账号状态会影响支付成功率。
- 长按识别二维码在旧微信版本上体验可能弱于官方微信支付。
- 虎皮椒仍是中间态；长期最优仍是 ADR-006 的个体工商户 + 官方微信支付。

## 待用户提供

上线前需要用户提供并只写入生产 `.env`：

- `HUPIJIAO_APP_ID`
- `HUPIJIAO_APP_SECRET`
- `HUPIJIAO_WEBHOOK_SECRET`
- 虎皮椒后台 webhook URL：`https://<微信云托管默认域名>/api/v1/webhook/hupijiao`
- 确认虎皮椒当前是否支持个人主体注册和稳定收款

## 关联

- ADR-003：MVP 变现路径仍保留客服扫码兜底。
- ADR-006：个人主体官方微信支付限制仍成立；虎皮椒是自动化过渡方案。
- ADR-012：MVP 期 webhook URL 使用微信云托管默认 HTTPS 域名。
- PRD §4.8：Paywall 与支付订单流程。
- FUTURE_WORK #6：长期升级为个体工商户 + 官方微信支付。
