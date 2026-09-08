# Studio V1 开发预览验收

## 2026-09-08 社交素材与头像（已发布）

- 代码提交：`98b395b`；分支 `codex/studio-v1-20260907` 已推送 GitHub。
- 发布版本：`20260908133654-studio-v2`；构建标识 `2026-09-08T13:34:02.771Z`。
- 发布包：20,069,529 字节、158 个受清单校验的文件；SHA-256 `6e9a0301d6ec3870963f8a2ac0998e7f1ffd4d5e47793d10e2801a686cf58875`。
- 源站 current 已切至 `/opt/pindou/studio/releases/20260908133654-studio-v2`；回滚备份 `/opt/pindou/studio/backups/20260908133654-studio-v2`。
- 公网 HTML 与 `version.json` 已确认新构建，主资源 `index-DKocNOu4.js` / `index-Du564rQ9.css`。
- 微信、小红书、加拿大国旗 SVG、原头像 PNG、Simple Icons 许可共 5 个归档来源文件，公网 SHA-256 与来源记录全部一致；SVG Content-Type 为 `image/svg+xml`。素材清单和复用方式见 `03_design/STUDIO_BRAND_ASSETS.md`。
- 本地 9 组：Chromium 中英文各 320/390/768/1440px，WebKit 390px 触屏/微信 UA 模拟；正式构建、43 模块文案锁、资源解码、日记标题/正文文本一致性、无横向溢出均通过。公网另检查 390/1440px，头像及三个图标正常，14 个带加拿大国旗的日记标题正常，无 JavaScript 异常。微信模拟不代表真机验收。
- 原生成器首页公网 200、原 JS 标识保留；源站旧 HTML SHA-256 仍为 `506f9bd2f9f0c37c52f08924f1504286816b93bff3198aea9f1790d0eceb36aa`；`pindou` 与 `pindou-studio` 均 active，Studio 公网健康检查 200。
- 本次为静态素材和展示组件更新，服务代码、经营配置和已批准文案无变更；没有创建真实预约或支付订单。检查与截图保存在忽略目录 `artifacts/studio-social-assets/`。

以下为 2026-09-07 首版的历史验收；当前业务规则以 `02_product/STUDIO_VISION2_PROGRESS.md` 为准。

---

验收日期：2026-09-07。
发布版本：`20260907204623-studio-v1`。
发布包 SHA-256：`2277b100d42ae4e6f910c51f76d3beff38f810c825915786b7ac4d77a7ba2bc4`。

## 可访问入口

- [工作室首页](https://pindoupuppy.com/studio/)
- [到店预约意向](https://pindoupuppy.com/studio/visit)
- [小店与自提询单](https://pindoupuppy.com/studio/shop)
- [工作室相册](https://pindoupuppy.com/studio/journal)
- [店主工作台](https://pindoupuppy.com/studio/manage)
- [原图纸生成器](https://pindoupuppy.com/upload)

## 已完成检查

| 检查 | 结果 |
| --- | --- |
| TypeScript / Vue 类型与生产构建 | 通过 |
| 后端自动测试 | 15 项通过 |
| 桌面 1440px、手机 390px 四个访客页面 | 无水平溢出、无坏图、无 JavaScript 异常 |
| axe WCAG 2 A / AA / 2.1 AA 自动检查 | 修正文字对比度后，8 个页面 / 视口组合均无检测问题；不等同完整无障碍认证 |
| 语言切换 | 中英界面切换、文档语言更新，正在填写的姓名和联系方式保留 |
| 图集 | 原图查看、前后切换、Escape 关闭 |
| 选购清单 | 品类筛选、增减数量、刷新保留、提交后清空 |
| 本地真实提交 | 两种设备的预约 / 自提均保存并返回真实编号 |
| 源站真实提交 | 两类请求保存、管理员可读、状态可更新；精确清理 2 条专用验收数据 |
| 防重复 | 相同幂等键重复提交返回原编号，不生成第二条记录 |
| 提交过程 | 提交期间锁定选购数量；服务器失败时保留填写内容，重试使用原幂等键并可成功保存 |
| 业务输入 | 拒绝过去日期、错误时间区间、非法商品 / 数量、缺少同意等输入 |
| 管理权限 | 未登录 401；有效 viewer 令牌仍被拒绝；完整 admin 经原后台核实后可管理 |
| 管理记录 | 状态变更有审计；过期版本更新返回 409，避免覆盖其他操作 |
| 公网路由 | 工作室全部页面 200，独立健康检查 200，管理数据匿名访问 401 |
| 静态资源 | 公网 JS / CSS 文件名与本地构建一致；缺失 JS 返回 404 |
| 原站点保留 | 原 HTML 中应用内容和 JS / CSS 版本未变；原健康检查正常；pindou 服务持续 active |

旧站点公网 HTML 可能按请求插入 Cloudflare Analytics 脚本。排除该边缘注入后，应用 HTML 相同。原构建资源为 `index-D_x1Yq-W.js` / `index-D-G8Azwh.css`；新工作室资源为 `index-DUEUEbo7.js` / `index-BuAy7bG0.css`。

公网桌面与手机的中英页面、正常动态效果、移动菜单、管理登录入口及旧生成器都通过浏览器检查。最终发布包含提交锁定与格式整理，公网构建哈希再次核对一致。

首屏与表单截图、自动检查 JSON 保存在本地 `artifacts/studio-qa/`，该目录被 git 忽略。工作室依赖的实际源站版本已记录在 `06_studio/requirements.lock.txt`。

## 当前边界和待确认信息

这是使用真实数据存储的开发预览，不是已启用在线付款的正式商城。价格暂根据店主公开价目图展示；费用、时段、座位和库存由店主确认。

店主工作台使用原后台账号；没有新增密码。当前没有自动通知，店主需进入工作台主动处理请求。顾客联系方式仅供店主管理使用，没有放进前端公开列表。

营业正文与图片存在 22:00 / 23:00 冲突。尚待确定最新营业安排、接待上限、停车 / 楼层说明、完整商品 SKU、库存、价格与税费，以及后续是否接在线支付。

此次新增全局项目 skill `pindou-studio-design`，与仓库 `.agents/skills/pindou-studio-design/SKILL.md` 一致并通过结构验证。上游设计 skills 已调研并记入设计文档；未安装 Impeccable 二进制 / hooks，也未接入高德 SDK。
