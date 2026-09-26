# Studio 默认英文与小店默认拼豆套装验收（2026-09-25）

店主要求：“一进入网站文字设置是英文的。一打开拼豆小店界面是在家拼豆-拼豆套装。”

## 变更范围

- 原语言按浏览器语言决定，且首次访问即自动写入 `puppy-studio-locale`，中文浏览器及老访客会一直显示中文。现默认英文，只记住访客手动切换（新键 `puppy-studio-language`），旧键不再读取。首页中文字体预加载改为仅在已选中文时进行。
- 小店默认根分类由 `refills`/`refill-a` 改为 `kits`；该分类被隐藏时仍回退到第一个可见分类。文案、服务端与数据库未改。提交 `374f970`。

## 验证与发布

- 本地：文案合同、Vue 类型检查、构建通过；QA 夹具（临时库、假支付网关）Chromium 验证中文浏览器首访英文、旧键 `zh` 仍英文、手动切中文刷新保持、小店默认在家拼豆/拼豆套装，无页面错误。
- 以生产 `20260924180611-studio-v7` 清单为基准，`studio_frontend_pack.py` 仅打包 56 个前端文件，621 个文件按原哈希复用，服务端文件未变。发布 `20260926001311-studio-v7`，677 个文件哈希有效，`pindou`/`pindou-studio` 保持 active。
- `studio_release_audit.py` 前后对比：Studio 与生成器业务表、受保护成员/账本、钱包文案、生成器首页哈希全部一致。
- 公网 `https://pindoupuppy.com`（中文浏览器 + 旧键 `zh`）：首页 `lang=en-CA`，小店默认 Bead at home → Bead kits；切中文刷新后保持中文、默认“拼豆套装”；无页面错误。

回退旧版为 `/opt/pindou/studio/releases/20260924180611-studio-v7`，自动备份为 `/opt/pindou/studio/backups/20260926001311-studio-v7`。本机忽略目录 `artifacts/studio-default-en-shop/` 保存前后审计与线上截图。
