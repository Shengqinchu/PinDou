# 中文社区拼豆深度调研

> Task I，2026-05-24  
> 目标：用国内公开社区、电商、工具线索校准 Task H 偏国际工具站的数据。

## 总结

- 国内实际市场更偏 **2.6mm 小豆 + MARD/COCO/黄豆豆/DODO/咪小窝/漫漫/盼盼**，而不是海外工具站常见的 Perler/Hama。
- MARD 仍是默认色卡的最稳候选，但 Phase 1 应至少把 `MARD 2.6mm` 作为隐藏实验规格；人像/宠物场景小豆更合理。
- Task H 需要补一个 `漫漫 / ManMan` 数据文件或明确映射关系。
- 价格 schema 必须拆 SKU 表：`price_per_1000pcs` 不足以表达平台、币种、包装、销量和置信度。
- 小红书公开 Web 无法合规自动采满 200 篇；本轮创建了 App 人工补采模板，避免登录态/私域/长文/图片入 git。

## 文件

| 文件 | 内容 |
|------|------|
| `xhs_color_mentions.csv` | 公开 Web 样本 + 小红书人工补采队列 |
| `xhs_manual_collection_template.csv` | 224 行 App 人工采样模板 |
| `xhs_kol_preferences.md` | KOL/内容偏好初判 |
| `bead_skus_cn.csv` | 102 条公开 SKU/价格/热度线索 |
| `brand_popularity_cn.md` | 国内品牌热度排序 |
| `community_insights.md` | 贴吧/B站/中文社区认知 |
| `competitor_palette_reverse.md` | 8 个上场工具公开反查 |
| `physical_vs_screen_delta.md` | 实物 vs 屏幕色差风险与 30 个优先实测色号 |
| `cn_supply_status.md` | 供应链状态报告 |
| `china_market_status_overrides.json` | 55 条供应链状态覆盖层 |
| `chinese_color_aliases.json` | 120 条 MARD 中文别名 UI 映射建议 |

## 局限性

- 未登录小红书、淘宝、1688；没有抓私信、私群、评论个人信息或商家联系方式。
- 没有保存 KOL 图片、实物色卡照片、竞品输出图。
- 电商价格/销量来自公开页面、搜索摘要、镜像和报道，置信度按行标注。
- `chinese_color_aliases.json` 是 UI 映射建议，不等同官方色名；需要 App 人工样本继续校准。

## Phase 1 PRD 建议

1. 默认色卡：保留 MARD，但把“默认规格”从单一 MARD 5mm 调整为 `MARD 5mm 入门` + `MARD 2.6mm 人像/宠物隐藏实验`。
2. Schema：新增 `bead_skus`、`china_market_status`、`aliases_cn`、`source_confidence`，不要把所有价格塞到 palette row。
3. UI：色号搜索支持中文别名和口语词，例如“奶白、腮红粉、描边黑、透色”；图纸材料清单仍显示官方 code。
4. 运营：小红书内容不要讲抽象算法，讲“成品图 + 色号 + 尺寸 + 避坑 + 可购买清单”。
