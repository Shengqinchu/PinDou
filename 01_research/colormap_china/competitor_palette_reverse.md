# 已上场拼豆工具色卡反查

> 方法：只看公开前端页面、工具说明、公开搜索摘要；未登录、未注册、未上传真人图、未保存竞品输出图、未抓后端。

| 工具 | 类型 | 默认/支持品牌 | 色数口径 | 导出 | 结论 | URL |
|------|------|---------------|----------|------|------|-----|
| 拼豆星球 | web/app | MARD likely / MARD;COCO;ManMan;PanPan;MiXiaoWo;custom | 291/221/144/120 visible | download pattern; grid; color count | 国产色卡覆盖最强，需真机确认默认品牌和导出格式 | https://pindou.cn/ |
| 拼豆大师 Pro / 365-tools | web | Perler / Perler | unknown | PDF | 偏单品牌施工图纸工具 | https://365-tools.cn/detail/40 |
| 德虎造物 | web | MARD likely / MARD;COCO;漫漫;盼盼;咪小窝 | public summary says 295 | multi-format export | 国产五色卡覆盖强，动态工作台需实测 | https://dehumaker.cn/ |
| MakeBead | web | Perler Midi / Perler;Hama;Artkal S-5mm;Nabbi BioBeads | 103;92;199;30 | PNG;PDF | 公开说明完整，品牌切换清楚 | https://makebead.com/ |
| Bitbead | web | language-dependent, often Perler / Perler;Hama;Artkal;Artkal Mini;MARD 221/291 | 117;89;176;221;291 | PNG;PDF | MARD 覆盖好但不含 COCO/漫漫等国产卡 | https://bitbead.pomodiary.com/en |
| BeadMapper | web | Perler / Perler;Mard;Artkal A;Hama;Nabbi | 102;291;145;80;30 | Export | 本地处理，MARD 有但 COCO/漫漫缺失 | https://www.beadmapper.com/ |
| BeadPattern | web | unknown / MARD;COCO;Artkal;Perler;Hama | unknown | PDF;shopping list | 国产到 MARD/COCO，缺漫漫/盼盼/咪小窝 | https://beadpattern.net/about |
| 拼豆像素化助手 metamo | web | MARD / MARD;COCO;漫漫;盼盼;咪小窝 | unknown | CSV;color-number system list | 公开页面直接展示色号系统选择 | https://pindou.metamo.cn/ |

## 与 Task H 的偏差

- 中文工具普遍支持 MARD / COCO / 漫漫 / 盼盼 / 咪小窝，Task H 已覆盖 MARD / COCO / 咪小窝 / 盼盼，但 **漫漫 / ManMan** 需要补齐或映射。
- 海外工具色数口径差异很大：Perler 102/103/117，Hama 80/89/92，Artkal 145/176/199/221。Task H 的做法更稳，因为显式记录来源与置信度。
- 多数工具不公开豆径，容易把“品牌色卡”和“物理可混拼”混在一起；PinDou 应继续坚持 `brand + bead_diameter_mm`。
- 真机同图测试仍需要用户提供非真人/授权测试图并在浏览器或手机内操作：拼豆星球、德虎造物、BeadPattern、BeadMapper、MakeBead、Bitbead。
