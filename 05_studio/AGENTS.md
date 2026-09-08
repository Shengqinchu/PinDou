# Studio 文案与设计约定

用户明确要求：文案要落档、规范化、模块化；只有用户要求修改时才修改。

- 当前业务与逐项要求：`../02_product/STUDIO_VISION2_PROGRESS.md`。后续用户澄清优先于 PDF，第二版优先于第一版。
- 页面、错误、通知、辅助名称、中英文内容使用 `src/content/`。文案键稳定；不因排版、动效或重构更换文案、翻译、标点或插入新宣传语。
- `../02_product/copy/STUDIO_COPY_BE46A3D.json` 是变更前不可修改的基线。`STUDIO_COPY_CATALOG.md` 是当前内容目录；`STUDIO_COPY_RULES.md` 规定修改流程。
- 修改文案必须关联用户原话/PDF 页码/已确认要求，并写到 `STUDIO_COPY_CHANGES.md`。不得为通过检查无理由执行 `content-catalog.mjs --approve`。只有本次获得用户文案修改授权时才能更新批准哈希。
- 普通设计修正只运行 `npm run check:copy` 和 `npm run build`，不能自动改写批准文件。动态的时间、人数、订单等数据正常变化，不属于宣传文案修改。
- 使用 `../.agents/skills/pindou-studio-design/SKILL.md` 的当前规则。真实 logo 由 PDF 提取，实拍保持原貌。中文不再使用衬线标题；文字黑灰，页面白底、浅色点缀。图标不替代可读标签。
- 客户预约由服务端排班决定；管理员可编辑。新购买保持暂停。浏览器/微信模拟与真机测试须分别记录。
- `../05_web` 与 `../06_backend` 是已有生成器。不要把那些未提交修改纳入本任务提交。
