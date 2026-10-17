# ADR-013 量化与背景管线修订（杂色 + 背景豆 + 主色下采样）

- 状态：已采纳（2026-05-31）
- 决策人：用户 + chat 端 Claude
- 触发：实测"萌宠拼豆·AI 橘橘"(52×52) 对照原图（黑边/土灰/红项圈/白底的扁平贴纸），输出出现十几个脏色 + 整板被白底填满。原图本应 ≈3 色 + 透明底。

## 问题与根因

1. **背景被算成豆**：管线对整张图量化，白底成了浅灰豆铺满整板。`postprocess.detect_and_remove_white_bg` 已存在但不够狠（阈值严/未做边界连通泛洪），没真正去掉。
2. **杂色（十几色）**：
   - 下采样用 LANCZOS（`quantize.py:48`、`builder.py:233`）平滑插值，黑边与土灰交界被平均成中间脏色。
   - 调色板 K 偏高，k-means（`quantize_core.select_palette_colors`）拿簇去拟合抗锯齿中间色。
   - 量化后无"近似色按 ΔE 合并"步骤（`merge_small_components` 是空间小区域合并，非颜色合并）。

## 决策

按以下顺序改造管线（本 ADR 范围 = 扁平/干净背景图，照片类 ML 抠图见"未决"）：

1. **背景去除前置**：强化 `detect_and_remove_white_bg` 为"从四边界做容差泛洪(flood fill)"，连通到边缘且接近背景色(近白/主导边缘色)的像素 → 透明；背景格 = 空(NoBead)，不出豆、不占调色板名额。
2. **主色下采样**：每个格子取**主导色(众数/area-dominant)**而非平均/LANCZOS 插值。黑就是黑、土灰就是土灰，不再发明中间色。
3. **调色板 ΔE 合并**：k-means 出色后，对 ΔE(CIEDE2000) < 阈值的近似色合并回主色并重新指派。
4. **扁平图自动压低 K**：检测"主色面积高度集中(前 N 色覆盖 >阈值)"=扁平插画 → K 压到 4-6；照片(色彩分散)保留较高 K。条件触发，不一刀切。
5. **去掉"估算成本"展示**：前端 `result/basic.vue`、`result/premium.vue` 两处移除（后端 cost_estimate 字段可留，不展示）。

依赖顺序：①背景去除 → ②③④ 量化。去背景后调色板不再被白底占用，杂色一并改善。

## 验收
用这只狗(萌宠·AI 橘橘原图)做基准：输出必须 **透明底 + ≤5 个干净色**(黑/土灰/红/可选)，整板不再被背景填满。

## 低格数特征/轮廓保留（2026-05-31 实测补充）

主色下采样修好了脏色（4 色干净），但低格数（26×26）下出现新问题：黑色轮廓断裂成碎点、眼睛/嘴/红项圈等关键特征被面积投票清零（红项圈仅剩 7 颗），整图不可辨。52/104 正常。
- **根因**：主色(众数)下采样在大格子下，细结构（轮廓/小特征）面积小、斗不过大片填充色，被丢弃。
- **决策**：在主色法之上加"边缘/特征优先"层——轮廓优先采样（格内含足够轮廓像素则强制轮廓色）+ 关键特征最小存在保底 + 低格数沿前景边界补 1 豆宽轮廓。前景填充仍用主色，结构线走边缘优先。

### 算法依据（调研锚点，中英文 + 论文）
- **[Zippland/perler-beads 七卡瓦](https://github.com/Zippland/perler-beads)**（中文开源标杆，React+Vite+WebWorker）：其"主导色像素化 + 边界 flood-fill 去背景 + BFS 杂色合并 + 多品牌色卡"**与本 ADR 第 1 版架构高度一致 → 验证我们方向正确**。
- **[liangdabiao/perler-beads-ai](https://github.com/liangdabiao/perler-beads-ai)**：上者的 AI 优化分支。
- **[cornelk/beadmachine](https://github.com/cornelk/beadmachine)**：Go 成熟实现，参考调色板/输出。
- **[Kopf 等《Content-Adaptive Image Downscaling》(微软研究院)](https://johanneskopf.de/publications/downscaling/paper/downscaling.pdf)**：双边高斯核降采样，保留线性特征/边缘，专为"矢量图→像素画"，不糊边 → **低格数保轮廓的学术金标准**。
- **[Edge-Aware Pixelation (yogthos)](https://yogthos.net/posts/2025-12-11-edge-aware-pixelation.html)**：自适应网格，语义保留人脸/文字/轮廓。
- **[Hiivelabs 自适应降采样(含 Python 代码)](https://hiivelabs.com/blog/gamedev/graphics/2025/01/19/adaptive-downscaling-pixel-art/)**：实战实现，处理边缘+透明。
- 注意：参考思路/算法，勿整段拷贝他人代码（先看 license，避免污染）。

## 未决（后续 ADR / FUTURE_WORK）
- **照片类(人像/宠物实拍，背景非纯白)**：泛洪去白底无效，需 ML 抠图(rembg/u2net) 出 alpha 遮罩。本 ADR 不含，留作下一步——因为产品真实主场景是实拍照片，此项优先级高，紧随其后。
