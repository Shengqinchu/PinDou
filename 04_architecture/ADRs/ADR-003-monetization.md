# ADR-003: 变现结构 - AI 积分 + 普通时间卡

- **状态**: Accepted（2026-06-07 修订）
- **日期**: 2026-05-24（首版）/ 2026-06-07（积分账本修订）
- **决策者**: 用户 + Claude Code + Codex
- **影响范围**: 额度账本、生成扣费、CDK、虎皮椒支付、后台补发、前端定价弹窗

## 背景

旧模型把 `paid_credits` 当作 AI 次数，并让 `monthly_card_expires_at` 同时覆盖普通生成和 AI 生成。这会导致一个关键错账：用户购买月卡后 AI 生成也免扣费，而新定价要求 AI 始终有明确成本。

因此变现模型改为两条并行权益：

- **积分**：只用于 AI 模式。AI 生成统一 128 积分/张。
- **时间卡**：只用于普通脚本模式及普通路径的高清/无水印/分板权益，不抵扣 AI。

## 决策

### 1. 积分与时间卡

| 权益 | 用途 | 规则 |
| --- | --- | --- |
| 积分 | AI 模式 | 128 积分/张；生成成功才最终扣除，失败释放预占 |
| 时间卡 | 普通模式 | 有效期内普通脚本生成不限次；不抵 AI |
| 注册礼 | 新用户 | 3 次普通额度 + 188 赠送积分，赠送积分 7 天有效 |

`staywithcsq@outlook.com` 等配置在 `UNLIMITED_CREDIT_EMAILS` 的白名单账号仍保留无限权益，用于测试和运营。

### 2. 定价

#### 积分包（实充，永久）

| 套餐 | 价格 | 积分 | 约 AI 张数 | 副文案 |
| --- | ---: | ---: | ---: | --- |
| 体验包 | ¥0.99 | 200 | 1 张，余 72 | 先试一张 AI |
| 标准包 | ¥9.9 | 1200 | 9 张，余 48 | 日常够用，更划算 |
| 超值包 | ¥29.9 | 4000 | 31 张，余 32 | 一次充够，最省 |

#### 时间卡（普通无限 + 随卡赠积分）

| 卡 | 价格 | 随卡赠分 | 有效期 | 副文案 |
| --- | ---: | ---: | ---: | --- |
| 周卡 | ¥9.9 | 588 | 7 天 | 普通图纸一周无限 |
| 月卡 | ¥19.9 | 1888 | 30 天 | 普通无限 + 1888 积分 |
| 季卡 | ¥49.9 | 6888 | 90 天 | 长期最省 |

实充积分不过期；注册礼和时间卡赠送积分按 `expires_at` 惰性过期。余额查询永远只统计未过期 grant，清理任务只做归档，不作为正确性依赖。

### 3. 账本真相源

新增积分账本：

- `credit_grants`：积分来源桶，含 `amount_remaining`、`amount_reserved`、`kind=paid|gift`、`expires_at`。
- `credit_transactions`：流水，记录 grant/reserve/consume/release/transfer 等操作。

旧字段保留为兼容缓存：

- `User.free_credits_remaining`：普通模式注册送的 3 次。
- `User.paid_credits`：兼容显示用，按 `可用积分 // 128` 同步，不再是真相源。
- `User.monthly_card_expires_at`：兼容旧字段。
- `User.membership_expires_at`：新时间卡字段。

迁移时将旧 `paid_credits > 0` 转成永久 paid grant，将旧 `monthly_card_expires_at` 复制到 `membership_expires_at`。

### 4. 扣费与并发

AI 生成采用 reservation 模型：

1. 提交 AI 任务时预占 128 积分。
2. 后台任务成功后将 reservation 转为 consume。
3. 失败或取消时 release 回原 grant，保留原 grant 的过期时间。

扣减必须是原子操作，使用条件更新 `amount_remaining >= chunk`，避免两个 AI 请求同时读到同一余额后双花。测试必须覆盖并发两请求只成功一个的场景。

### 5. 扣费顺序与过期

扣费顺序：

1. 先扣最快过期的赠送积分。
2. 再扣不过期实充积分。

过期正确性由查询条件保证：`expires_at IS NULL OR expires_at > now`。定时清理任务漏跑也不能让过期赠分继续可用。

### 6. CDK

新 CDK 类型：

- `points`：兑换指定积分数。
- `membership`：兑换指定天数时间卡。

旧 CDK 类型继续兼容：

- `single_use` / `credit_pack_5` / `credit_pack_10`：按 `value * 128` 转积分。
- `monthly_card`：按 `value` 天时间卡兑换；`value <= 1` 时按 30 天兼容。

匿名 CDK 和匿名余额迁移到注册账号是后续批次（B4），应绑定设备指纹并在注册时迁移 grant。

### 7. 支付

虎皮椒 SKU 使用 6 个新档位：

- `points_trial_099`
- `points_standard_990`
- `points_value_2990`
- `membership_week_990`
- `membership_month_1990`
- `membership_season_4990`

支付回调发放权益必须幂等。订单已进入 paid 状态但权益未到账时，重复 webhook 或后台补发应再次尝试发放，而不是因为订单已支付就直接忽略。

旧支付 SKU 仅作为历史订单兼容保留：

- `single_9.9`：历史订单发 128 积分；新建订单 alias 到 `points_standard_990`。
- `monthly_28`：历史订单发 30 天时间卡；新建订单 alias 到 `membership_month_1990`。

## 后果

### 正面

- AI 成本清晰，时间卡不会误放大为 AI 无限。
- 积分账本支持实充、赠送、过期、预占、失败释放和流水审计。
- 支付/CDK/admin 都能走同一套发放和扣费逻辑。

### 风险

- UI 仍需改成“积分 + 时间卡”双面板，否则前端文案会与后端新账本不一致。
- 老 `paid_credits` 只做兼容缓存，后续代码不得再直接把它当真相源扣减。
- 若存在旧 `monthly_28` 真实付费用户，AI 从“月卡免费”改为 128 积分/张属于产品规则变更，上线前需确认是否需要补偿。

## 分批

- **B1 已实施**：积分账本、AI 128 reservation/consume/release、注册礼积分、旧 `paid_credits` 惰性迁移、并发测试。
- **B2 已实施**：`membership_expires_at` 时间卡、普通模式时间卡不限次、时间卡不抵 AI。
- **B3 已实施核心规则**：注册赠送积分、赠送积分惰性过期、扣费顺序；清理任务仅作为后续归档优化。
- **B4 待实施**：匿名 CDK/设备账本、匿名注册迁移。
- **B5 已实施后端**：6 个虎皮椒 SKU 和幂等发放；前端定价弹窗待 UI 批次。
- **B6 已实施**：web 定价弹窗双面板、账户钱包展示、CDK 兑换入口、生成前低余额拦截。

## 关联

- ADR-011：虎皮椒支付码与客服兜底。
- FUTURE_WORK #9/#13：限频和后台风控需用持久化计数，不依赖进程内状态。
- 06_backend `credit_service.py`：积分账本真相源。
