# ADR-005: AI 风格化技术方案 — 多路线 + 风格分流 + Fallback Chain

- **状态**: Accepted
- **日期**: 2026-05-24
- **决策者**: 用户 + chat 端 Claude
- **影响范围**: 后端核心算法、成本结构、合规、Phase 0 PoC 验收

## 背景
拼豆图纸的真实人像失真问题，业界普遍未解决。卡通可用脚本量化糊过去，但人像 / 宠物 / 情侣场景需要语义级理解。不同风格预设对"身份保持 vs 风格自由"的权衡不同，单一技术栈无法兼顾。

## 决策

### 按风格预设分流主路线
| 风格预设 | 主推技术路线 | 备选 | 理由 |
|----------|-------------|------|------|
| 写实人像 | SD + IPAdapter(Face) + ControlNet(Depth) | 国产 API | 必须像本人，几何强约束 |
| Q 版人像 | gpt-image-1（反代）| 即梦 | 允许变形，语义控制更好 |
| 宠物 | gpt-image-1 + ControlNet(Canny) | 即梦 | 介于两者之间 |
| 通用卡通 | gpt-image-1（创意发挥）| 即梦 | 风格自由 |

### 架构约束（硬性）
1. **统一抽象为 `StylizationProvider` 接口**，配置驱动可动态切换 provider。
2. **必须实现 fallback chain**：主路线 → 备选 1 → 备选 2 → **普通量化兜底**（保证产品永远能出图，绝不让用户看见纯报错）。
3. **接口设计在 Phase 1 PRD 中明确**，避免后期更换 provider 影响业务层。
4. **Prompt 工程分层**：
   - 写实人像强约束："preserve exact facial features, identity, expression; only change rendering style to N-bit pixel art; do not alter proportions or features"
   - Q 版放松约束，允许风格化变形

## 理由
- 真实人像和卡通的最优技术栈不一致，必须分流。
- Fallback chain 解决反代稳定性 + 单一 provider 故障 + 极端审核失败问题。
- 抽象接口为 Phase 2 替换合规 provider 留出空间。

## 后果
- 正面：质量 + 可用性双优化；反代成本可忽略支持研发期试错。
- 负面：四条路线维护成本 = 4×单路线；Prompt 工程跨 provider 差异需要持续 tune。
- 风险（已识别并记录）：
  - **反代 gpt-image-1 用于生产存在 AIGC 备案合规风险**：Phase 2 启动算法备案，或将主路线切换到国产合规通道（火山 / 阿里通义）。
  - **反代稳定性风险**：fallback chain 是硬性兜底，必须 Phase 1 集成时即落地。
  - **用户已知风险并选择此方案**：研发成本可忽略，效果待 PoC 数据决定。

## 备选方案
- **单一 SD 自部署**：被否，写实人像之外的风格预设效率不如 API。
- **单一国产 API**：被否，国产 API 对人像 ID 保持能力当前测试不足，需 PoC 验证。
- **不做 AI 预处理纯量化**：被否，丧失差异化竞争力，与 ADR-003 付费分层冲突。

## PoC 验收（Phase 0 任务 C）
该 ADR 的具体技术路线由 Phase 0 PoC 的实测数据最终确认；若 PoC 表明某风格预设的主推路线效果不及备选，**允许在 ADR-005a 修订中调整分流表**。架构层面（接口抽象 + fallback chain）不因 PoC 结果改变。
