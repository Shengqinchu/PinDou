# Gemini Phase 2 设计 + 前端 Brief

**Status**: pending
**Owner**: Gemini
**Priority**: P0
**Estimated**: 3-4 周（含 4 个子任务，与 Codex 后端并行）
**前置**: Phase 1 PRD v1.0 已冻结（`02_product/PRD_v1.0.md`）

---

## 前置阅读（必读）

按顺序读：
1. `02_product/PRD_v1.0.md`（**实施合同**，特别 §3 用户路径 / §4 功能清单 / §7 UX 规范）
2. `04_architecture/ADRs/ADR-001/003/004/006/008/009`（最相关）
3. `00_meta/PROJECT_CHARTER.md`（项目目标 + 用户画像）
4. `01_research/competitor/business_models.md`（竞品视觉参考）
5. `08_growth/xhs_playbook.md`（小红书运营调性）
6. `01_research/tech/perler_bead_domain_notes.md`（拼豆领域知识）

---

## 技术栈（已定）

- **小程序框架**：uni-app（Vue 3 + setup script），支持后续 Web 端复用
- **UI 组件库**：uView 3 或 wot-design-uni（按设计风格选）
- **状态管理**：Pinia
- **HTTP**：uni.request 封装
- **构建**：HBuilderX 或 Vite CLI

---

## 设计调性（来自 PRD §7.5 + 用户画像）

- 目标用户：女性 70% / 18-35 岁 / 小红书风格
- 视觉风格：**清新 / 可爱 / 少女感**
- 主色：粉色 / 米色系（避免冷感）
- 字体：圆润感（避免硬棱角）
- 关键 CTA：高饱和粉 / 渐变橙
- **不要**做"高端商务感 / 工业风 / 极简黑白"

---

## 任务分解（4 个子任务）

### 任务 1：设计系统（出独立 Figma / Sketch 文件）

#### 1.1 视觉规范
- 主色板（4-6 色）+ 辅助色板（强调 / 警告 / 成功 / 信息）
- 字体规范（标题 / 正文 / 注释三档字号 + 粗细）
- 间距规范（4 / 8 / 16 / 24 / 32 px 阶梯）
- 圆角规范（卡片 12px / 按钮 8px / 标签 4px）
- 阴影规范（浅 / 中 / 深三档）
- 插图风格（如有，统一手绘 / 几何 / 涂鸦）

#### 1.2 组件库
按 PRD 用户路径需要的组件：
- Button（主 / 次 / 文字 / 危险）
- Card（作品卡 / 选择卡 / 价格卡）
- Input（文本 / CDK 兑换专用 18 位）
- Toast / Modal / ActionSheet
- ProgressBar（生成等待用，PRD §7.1）
- Tag / Badge（颗数 / 价格等）
- Tab（首页 / 我的）
- Avatar + UserCard

#### 1.3 输出
- 完整 Figma 文件（含组件库 + 样式 token）
- `03_design/design_system/` 下产出：
  - `color_tokens.json`
  - `typography.md`
  - `components_overview.md`
  - `figma_link.md`（链接 + 截图存档）

### 任务 2：关键页面线框 / 高保真稿

按 PRD §3 用户路径，至少出 12 个关键页面：

| # | 页面 | 优先级 |
|---|------|--------|
| 1 | 首页（爆款展示 + 上传 CTA） | P0 |
| 2 | 上传图过程 + 预检 | P0 |
| 3 | **生成方式选择（脚本 vs AI 卡片对比）** | P0（关键差异化） |
| 4 | 风格 + 尺寸预设选择 | P0 |
| 5 | Preview 生成等待页（趣味文案 + 进度条） | P0 |
| 6 | FinishedPreview 展示 + 操作（重生成 / 切风格 / 加入待制作） | P0 |
| 7 | PatternSheet 展示（基础版） | P0 |
| 8 | PatternSheet 展示（高级版 PDF / Excel / 分区图） | P0 |
| 9 | 付费弹窗（加客服扫码 + CDK 入口） | P0 |
| 10 | CDK 兑换页 | P0 |
| 11 | 用户作品集 | P0 |
| 12 | 我的页面（额度 / 月卡 / 客服） | P0 |

每个页面：低保真（线框）→ 高保真（设计稿）→ 标注 / 切图

输出：
- `03_design/wireframes/` 下每个页面一个文件夹（线框 + 高保真 + 标注）
- 主交付：`figma_link.md` 含可点击原型链接

### 任务 3：小程序前端实现（uni-app）

按 PRD §3 用户路径 + 任务 2 设计稿，实现：

#### 3.1 项目结构
```
05_frontend/
├── pages/
│   ├── index/             # 首页
│   ├── upload/            # 上传流
│   ├── generate/          # 生成方式选择 + 风格 + 尺寸
│   ├── preview/           # FinishedPreview
│   ├── pattern/           # PatternSheet 展示 / 导出
│   ├── payment/           # 付费 / CDK 兑换
│   ├── artwork/           # 我的作品集
│   └── user/              # 我的
├── components/            # 复用组件
├── store/                 # Pinia
├── api/                   # 后端 API 封装
├── utils/
├── static/
├── App.vue
├── main.ts
├── manifest.json          # 小程序 AppID 等
└── pages.json
```

#### 3.2 API 对接
- 完全按 PRD §5 接口契约调用 Codex 后端
- 错误统一处理（PRD §7.2：永远不显示英文 / 技术细节）
- 加载态 / 重试 / fallback 流畅

#### 3.3 关键 UX 实现（PRD §7）
- **等待 UX**（§7.1）：进度条 + 10 句池子趣味文案 + "去看示例作品" 按钮 + 30/60 秒分段提示
- **错误提示**（§7.2）：中文友好文案，三类失败都有兜底
- **首屏 5 秒**（§3）：3 张爆款轮播 + 一键 CTA
- **双路径卡片**（§4.2）：必须用**同一原图**生成两个示例图做对比

#### 3.4 监控埋点（基础）
- 关键漏斗事件：进入 / 上传 / Preview / PatternSheet / 付费
- 错误日志（不含 PII）

### 任务 4：交付物 + 评审节点

#### 4.1 评审节点
- 任务 1 完成 → 用户 review 设计系统调性
- 任务 2 完成 → 用户 review 高保真稿（**最关键的 review 点**）
- 任务 3 完成 50% → 用户体验首版可点小程序原型
- 任务 3 完成 100% + 任务 4 完成 → Phase 2 验收

#### 4.2 交付物
- Figma 完整文件 + 截图存档
- 小程序代码（HBuilderX 可直接打开 / 预览 / 上传）
- 前端 README（含本地启动 / 调试 / 打包流程）
- 设计交付清单（图标 / 切图 / 字体 / 字符串国际化文件）

---

## 必须遵守

### 1. 接口契约不可破
- 严格按 PRD §5 + Codex 后端实现的 API
- 任何字段不匹配先在 `_questions_for_user.md` 提，**不要自己改后端字段名**

### 2. 私人素材（ADR-009）
- 前端测试 / 截图 / 示例图绝对不用真人照片
- 用 AI 生成假人脸 / 抽象图 / CC0 素材
- 用户作品集功能开发不存真实用户图

### 3. AIGC 标识（PRD §8.1 + Task F 合规）
- FinishedPreview 展示页**必须**标注"AI 辅助生成"
- 分享卡片 + 保存到相册的图都要有 AI 标识水印

### 4. 客服扫码付 UX 不要做得太突兀
- 付费弹窗里**优先**展示"输入 CDK"按钮（更顺畅）
- 客服扫码二维码 + 订单号要清晰可长按识别
- 引导文案："加客服微信确认订单后开通额度"

### 5. Commit 规范
- 分支：`phase2`
- 子任务完成后 commit：`feat(design-taskN): ...` / `feat(frontend-taskN): ...`
- 每完成一个任务在 `_questions_for_user.md` 加阶段汇报

---

## 与 Codex 后端协作

- **共享分支**：`phase2`（前端代码在 `05_frontend/`，后端代码在 `06_backend/`）
- **共享文档**：PRD §5 API + §6 数据模型 + `_questions_for_user.md`
- **冲突处理**：接口字段不匹配 → 提到 `_questions_for_user.md` → 用户 / Claude Code 拍板
- **进度同步**：Codex 任务 5（API）完成才能前端真正联调；之前用 mock 数据

---

## Phase 2 完成 → Phase 3（小程序提审 + 内测）

Phase 2 完成 = 前端可在微信开发者工具完整跑通 + 后端可在上海机部署 + 用户作品端到端无 bug。
Phase 3 启动条件 = 上述 + ICP 备案完成 + 用户协议 / 隐私政策上线 + 内容审核接入。
