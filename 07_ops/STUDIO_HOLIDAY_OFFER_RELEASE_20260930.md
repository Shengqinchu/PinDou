# 2026-09-30 网站预约页双节特惠发布

## 店主要求与最终页面

来源：店主“更新网站”及标注截图 `codex-clipboard-5b5b3720-a7a3-46fc-bd7d-e89330a0e2f7.jpg`。

- `/visit` 右下角储值标题改为“储值优惠”，保留 CAD 7／小时和原条件 info 按钮。
- 旧开学优惠、双人套餐和卡套套餐的展示替换为“双节特惠 至10.7”“新朋友可免费体验1小时”“老友带新友可同享（游玩3h起）”，同步英文。
- 沿用三种可选体验和一个资讯卡片的布局、现有字体、圆角、浅色背景及按钮；手机单列、英文自然换行，未增加内部滚动。
- 新增四个 `visit-flow` 键，服务端默认文案同步，以便店主编辑。既有套餐文案键、价格与记录仍保留；原生小程序已上传包没有重新构建或替换。本次为网站展示更新，不改变结算、预约时长或积分规则。

## 发布身份

- 生产目标：`36.139.201.94`，主机名实测 `19558948263`。
- 原 Studio current：`20260929183717-studio-v7`。
- 新 Studio current：`20260930162351-studio-v7`。
- 网站构建标识：`2026-09-30T16:20:14.513Z`。
- 产品提交：`e7f2206`；隔离分支 `codex/studio-holiday-offer-20260930`。
- 发布包 SHA-256：`0a8434ec3615aa599d709494cee53c95ebf5301fda64a3db514b5d9bd48dbd6c`。
- 使用 `studio_frontend_pack.py` 基于当前线上 manifest 打包：53 个网站文件及 `service/content-defaults.json` 更新，1094 个文件原字节复用，1148 个发布文件全部核验通过。
- 发布前双库一致性备份：`/opt/pindou/studio/backups/20260930162351-studio-v7-preflight/`。标准部署回退记录：`/opt/pindou/studio/backups/20260930162351-studio-v7/`。共享库持续保留，不用旧库覆盖新业务数据。

## 验收证据

- `npm run check:copy`、Vue 类型检查和正式构建通过；84 个文案模块只有 `visit-flow` 哈希变化，新增文字字体覆盖完整。
- 本地 Chromium/WebKit、中英文、320–1440px 共 9 组检查通过；桌面卡片与下一步可同时显示，手机无横向溢出。info 支持焦点、点击、Escape 和外部关闭；三种体验选择与下一步正常。
- 发布后公网 Chromium 1366×768、WebKit 390×844，中英文共 4 组检查通过；实读 `/version.json` 与本次构建一致。浏览器只读验收，未提交预约、发送顾客消息或进行真实扣款。
- Studio 18 个受保护业务表、生成器 6 个受保护业务表、76 个内容模块、4 个商品订单表和 3 个布贴活动表的发布前后指纹一致。
- 两个 SQLite 库 `integrity_check=ok`；会员时长、账本、原始日记、已发布/草稿覆盖和既有赠送保留。255 个商品及 6 个商品订单一致。
- `pindou`、`pindou-studio`、`nginx`、`cloudflared` 均 active；生成器 current、进程及入口哈希未变。Nginx 与 Studio unit 原字节保持，网站健康接口正常。

证据位于本次隔离工作区 `D:/Users/123/.codex/worktrees/pindou-holiday-offer-20260930/PinDou/artifacts/holiday-offer/`，包括 `local-browser/`、`live-browser/`、前后审计、发布日志及最终 `verification.json`。这些私有工件不提交 Git。
