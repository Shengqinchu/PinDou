# Studio 社交与头像素材

2026-09-08。来源授权：店主要求“搞一下微信和小红书的矢量图……保存一下小狗双吉这个头像图……比如我截图的地方……还有加拿大国旗”。本次仅增加素材和展示组件，未修改已批准文案。

## 可复用文件

所有文件保存在 `05_studio/public/studio-brand/`，线上路径统一为 `/studio/studio-brand/`。

| 文件 | 类型与用途 | 来源 |
|---|---|---|
| `wechat.svg` | 微信标识；24×24 viewBox，可任意缩放 | [Simple Icons 源文件](https://github.com/simple-icons/simple-icons/blob/develop/icons/wechat.svg) |
| `xiaohongshu.svg` | 小红书三字标识；24×24 viewBox，可任意缩放 | [Simple Icons 源文件](https://github.com/simple-icons/simple-icons/blob/develop/icons/xiaohongshu.svg) |
| `canada.svg` | 加拿大国旗；保留 2:1 比例及红白配色 | [Wikimedia Commons 源文件说明](https://commons.wikimedia.org/wiki/File:Flag_of_Canada.svg) |
| `xiaogou-shuangji-avatar.png` | 店主头像原图，376×376；当前用于页脚账号身份，后续可复用 | 店主提供的 PNG 附件，按原始字节保存 |
| `social-assets.json` | 下载来源、SHA-256、文件大小及头像来源记录 | 与上述文件同时归档 |
| `simple-icons-LICENSE.txt` | 两个平台 SVG 对应的 Simple Icons 许可原文 | [Simple Icons 许可](https://github.com/simple-icons/simple-icons/blob/develop/LICENSE.md) |

加拿大国旗的 2:1 比例与 11 角枫叶已对照[加拿大政府说明](https://www.canada.ca/en/canadian-heritage/services/flag-canada-description.html)核实。下载的 SVG 原文件未重绘、裁剪或改色。Simple Icons 的图形许可与平台品牌权利分别保留，不宣称图标由本项目原创。

头像 SHA-256：`01e7abcb8f4bdcb757fc3e7d76cd14b9ed15f0903410a0dc26fb747ce73e986c`。它是原始 PNG，并未伪装成矢量文件；白底、双狗轮廓、颜色均保持原样。本次不生成另一版狗形象，不替换 PDF 提取的店铺手写字标。

根目录 `.gitattributes` 禁止 Git 为这些 SVG 和许可原文转换行尾，确保 Windows、服务器或重新克隆仓库后的素材校验值保持一致。

## 使用方式

- `src/components/BrandIcon.vue` 接受 `name="wechat"`、`name="xiaohongshu"` 或 `name="canada"`。资源从本站加载，无远程运行时依赖。图标用于现有可读标签旁，作为装饰隐藏于辅助技术，避免重复朗读。
- 微信图标保留正方形画布。小红书使用 CSS 视窗去掉原 SVG 的上下空白，图形等比显示，原文件仍完整保留。加拿大国旗始终等比显示为 2:1，不套单色遮罩。
- 页脚的小红书链接加入原头像及品牌图标，微信号前加入微信 SVG，电话前加入加拿大国旗。手机联系区占整行，避免身份信息被挤到狭窄列中。
- `src/components/FlagText.vue` 在日记列表、文章标题和正文中呈现加拿大国旗 SVG。原国旗字符保留在可访问的隐藏文本中，其余文字原样显示；复制和 `textContent` 仍保留原文。组件不使用 `v-html`，不处理其他国家的旗帜，不改写 `journal-posts.json`。
- 后续页面需要相同标识时复用以上组件或原资源，不重复下载，不从截图抠图，不修改已批准文案来配合图标。

## 验证

- `npm run build` 通过，包括 43 个内容模块的文案锁定检查、Vue/TypeScript 检查及正式构建。`src/content/approved.json` 未修改。
- Chromium：320、390、768、1440 像素宽度，各检查中文与英文；WebKit：390 像素、触屏及微信 UA 模拟。共 9 组检查通过，无页面异常、横向溢出或资源解码失败。
- 核对 19 篇日记标题与原始数据完全一致；抽查本次涉及国旗显示的完整文章正文，文本保持一致。国旗实际显示比例为 2:1。
- 原头像的存档 SHA-256 与附件一致；SVG 不含脚本、外部资源引用或事件属性。
- 本地截图与检查记录位于忽略目录 `artifacts/studio-social-assets/`。微信结果属于浏览器模拟，并非真机验收。

部署记录见 `07_ops/STUDIO_VERIFICATION.md` 的“社交素材与头像”条目。
