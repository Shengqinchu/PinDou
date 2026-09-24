# 顾客消息与商品图片：发布验收

日期：2026-09-24（America/Toronto）。生产目标：`36.139.201.94`。

店主在 `575fa9ee19bdf0c95c3a416d0117baeb.png` 要求把顾客消息页“联系店主”改为“我的消息”，去掉输入框，只保留查看消息；在 `1b60f85c049acb334f837ea64cfa1494.png` 要求商品主图左右点击切换、下方缩略图可直接选图。网页顾客页现在使用只读对话，后台默认的回复功能保留；商品主图两侧各有上一张／下一张点击区域，首尾循环，缩略图换行且无水平滚动条。历史消息内容和原商品图片没有改动。

## 发布范围

- 原生产 release：`20260924152310-studio-v7`，417 文件哈希有效；新 release：`20260924155213-studio-v7`，469 文件哈希有效。
- 用 `studio_frontend_pack.py` 在生产清单上叠加构建产物：54 个前端文件更新，415 个既有文件按原哈希复用。43 个服务端文件全部保持原字节，旧哈希静态资源继续保留给已打开的页面。
- 标准发布流程将 Studio 数据库备份到 `/opt/pindou/studio/backups/20260924155213-studio-v7/studio.sqlite3`，回退前须先核对发布后的最新写入，不能覆盖新数据。
- 直达 `/messages` 原先被 Nginx 重定向至首页；发布后把该路径加入当前站点的 Studio 路由，并同步修改后续发布脚本。修改前配置备份：`/opt/pindou/studio/backups/20260924155213-studio-v7/nginx-before-messages-route.conf`。Nginx 配置检查、重载通过，公网 GET `/messages` 返回 200 且保持原路径。

## 验证与边界

- `npm run build` 包含文案批准哈希、Vue 类型检查与 Vite 构建，均通过；新增的按钮名称批准来源已记入 `02_product/copy/STUDIO_COPY_CHANGES.md`。
- `verify-readonly-messages-gallery.mjs` 在 1440×900 和 390×844 下分别检查本地构建与公网已发布页面：顾客标题、只读消息列表、无输入框；线上“小猫摇摇乐”10 张图片的缩略图数量、无水平溢出、左右切换、末张回首张和点击缩略图均通过。公网页面实际加载生产静态资源；消息接口使用隔离数据，不触碰真实顾客账号或发送消息。浏览器截图与结果在 Git 忽略的 `artifacts/messages-gallery-20260924/`。
- 发布前后 `studio_release_audit.py` 核对 Studio 与生成器服务均 active，469 个发布文件有效；受保护成员资料、非注册账本、生成器业务表、Studio 业务表和钱包文案摘要一致。审计摘要分别保存在同一 artifacts 目录的 `prod-before.json`、`prod-after.json`、路由修正后的 `prod-final.json`。
- 后台实际回复、真实顾客登录后的消息读取及手机微信内置浏览器没有本次端到端验证；本次只对用户要求的网页显示及公网可达性做了浏览器验收。
