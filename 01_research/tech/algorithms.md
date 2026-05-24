# Task B — 算法方案横评

> 执行日期：2026-05-24  
> Palette：`01_research/colormap/mard.json`（MARD 291 色）  
> 输出尺寸：100 x 100，目标色数：24 色  
> 测试图：三张非真实人物的合成图，避免真实人像授权风险

## 结论先行

Phase 0 的脚本量化基线建议：

- **写实人像**：K-means + CIEDE2000 + 无抖动（C02 / C12）
- **Q 版人像**：K-means + CIEDE2000 + Bayer（C07）作为候选，若想保干净块面则用 C02
- **宠物**：K-means + CIEDE2000 + 无抖动（C02 / C12）
- **通用卡通**：K-means + RGB + 无抖动（C01）或 K-means + CIEDE2000 + 无抖动（C02）；前者结构指标高，后者色差低

最重要的反直觉发现：**Floyd-Steinberg 并不总是更好**。在本轮 100x100 x 24 色的拼豆输出里，Floyd-Steinberg 抖动显著降低 SSIM，并在脸部/宠物毛色产生噪点；它更适合渐变色块，而不是需要干净五官和可读色块的拼豆人像。

## 测试集

| 输入 | 文件 | 说明 |
|------|------|------|
| portrait | `01_research/tech/test_inputs/portrait_synthetic.png` | 合成正脸头像，不对应真实人物 |
| pet | `01_research/tech/test_inputs/pet_synthetic.png` | 合成宠物头像 |
| cartoon | `01_research/tech/test_inputs/cartoon_synthetic.png` | 高饱和卡通图 |

## 组合矩阵

| ID | 量化 | 色差 | 抖动 |
|----|------|------|------|
| C01 | K-means | RGB | 无 |
| C02 | K-means | CIEDE2000 | 无 |
| C03 | K-means | CIEDE2000 | Floyd-Steinberg |
| C04 | Median-cut | CIEDE2000 | Floyd-Steinberg |
| C05 | Octree | CIEDE2000 | Floyd-Steinberg |
| C06 | K-means | CIEDE2000 | Atkinson |
| C07 | K-means | CIEDE2000 | Bayer |
| C08 | K-means | CIEDE2000 | Riemersma-inspired |
| C09 | K-means | CIE94 | Floyd-Steinberg |
| C10 | K-means | CIE76 | Floyd-Steinberg |
| C11 | Neural-gas baseline | CIEDE2000 | Floyd-Steinberg |
| C12 | K-means | CIEDE2000 | 无（C02 复跑对照） |

## 指标摘要

完整数据见 `01_research/tech/algorithm_metrics.csv`。

### 各输入按平均 CIEDE2000 最优

| 输入 | Top 1 | mean ΔE00 | SSIM | PSNR | 观察 |
|------|-------|----------:|-----:|-----:|------|
| portrait | C02 / C12 | 3.2773 | 0.9624 | 28.8256 | 皮肤、头发和五官边界最稳 |
| pet | C02 / C12 | 3.3552 | 0.9536 | 30.4168 | 毛色块面干净，鼻眼轮廓清楚 |
| cartoon | C02 / C12 | 5.3323 | 0.8901 | 24.8328 | 色差最低，但部分高饱和结构不如 RGB |

### 各输入按 SSIM 最优

| 输入 | Top 1 | SSIM | mean ΔE00 | 观察 |
|------|-------|-----:|----------:|------|
| portrait | C01 | 0.9667 | 3.8375 | RGB 保结构，但肤色感知色差更大 |
| pet | C01 | 0.9605 | 4.3262 | 结构好，颜色略偏 |
| cartoon | C01 | 0.9242 | 6.3369 | 卡通硬边结构保留最好 |

## 算法观察

### K-means

适合场景：人像、宠物、卡通的默认基线。  
不适合场景：极小图或只有极少色块时会产生重复候选色，需要补足 palette。

K-means 在本轮里稳定胜出。原因是先从图像本身抽 24 个代表色，再映射到 MARD 实体色，能同时保留主体块面和有限色号约束。

### Median-cut

适合场景：快速生成粗略 palette。  
不适合场景：肤色和低饱和渐变。

Median-cut + Floyd 的 C04 在三张图上 SSIM 和 ΔE00 都不占优。它容易把肤色拆成颗粒感更强的局部色，拼豆图看起来脏。

### Octree

适合场景：速度敏感、卡通图初筛。  
不适合场景：人像、宠物主输出。

Octree 比 Median-cut 略稳，但与 K-means 仍有明显差距。作为后端 fallback 可以保留，但不建议默认。

### Neural-gas baseline

适合场景：后续做研究型探索。  
不适合场景：MVP。

C11 的 neural-gas 基线没有超过 K-means，运行时间更高，调参空间也更大。Phase 1 不建议投入，除非后续发现 K-means 在真实照片上有明显瓶颈。

### 色差度量

- RGB：结构指标常常更高，尤其卡通硬边图；但对肤色和近似色的人眼观感不稳。
- CIE76：在 Floyd 抖动下最差，说明简单 Lab 欧氏距离不足以支撑实物色卡。
- CIE94：略好于 CIE76，但没有超过 CIEDE2000。
- CIEDE2000：平均色差最低，适合做默认色卡匹配。

### 抖动

- 无抖动：人像和宠物最干净，最像“可施工图纸”。
- Floyd-Steinberg：过渡更细，但脸部/毛发噪点重。
- Atkinson：比 Floyd 柔和，但结构指标仍低。
- Bayer：保留一点像素颗粒感，卡通/Q 版可试。
- Riemersma-inspired：本轮不占优，除非后续用 Hilbert 曲线实现完整版本，否则不建议默认。

## 主观对比图

- `01_research/tech/algorithm_samples/compare_portrait.png`
- `01_research/tech/algorithm_samples/compare_pet.png`
- `01_research/tech/algorithm_samples/compare_cartoon.png`

每张图包含 12 个组合，单项输出也保存在同目录，例如 `portrait_C02.png`。

## 推荐路线

| 风格预设 | 推荐组合 | 原因 | Phase 1 建议 |
|----------|----------|------|--------------|
| 写实人像 | C02 / C12 | 最低 ΔE00，脸部块面干净 | 默认关闭抖动，提供“细腻纹理”开关 |
| Q 版人像 | C07 或 C02 | Bayer 有像素感，C02 更干净 | UI 可给“干净 / 像素颗粒”二选一 |
| 宠物 | C02 / C12 | 毛色、眼鼻轮廓平衡最好 | 默认无抖动，局部手工编辑修毛边 |
| 通用卡通 | C01 或 C02 | C01 结构强，C02 色差低 | 根据用户选择“结构优先 / 色彩优先”切换 |

## 对 Task C 的输入建议

Task C 的 AI 预处理 PoC 应优先把 AI 生成图接到 **K-means + CIEDE2000 + 无抖动**。原因是 C 需要判断“量化输出图像不像本人”，脸部噪点会显著干扰志愿者评分。

建议额外输出一组 C07（Bayer）给 Q 版 / 卡通作为视觉备选，但不要把 Floyd-Steinberg 作为写实人像默认。

## 复现

```bash
python 01_research/tech/algorithm_impls/make_test_inputs.py
python 01_research/tech/algorithm_impls/run_benchmark.py
```

单独运行示例：

```bash
python 01_research/tech/algorithm_impls/quantize_kmeans.py \
  01_research/tech/test_inputs/portrait_synthetic.png \
  01_research/tech/algorithm_samples/manual_portrait.png \
  --metric ciede2000 --dither none
```

## 局限

- 本轮使用合成图，不等同真实手机照片；Task C 仍需用户授权素材或 AI 假人脸样本。
- Neural 方案只是轻量 neural-gas baseline，不代表完整论文级 neural color quantization。
- Riemersma 为 serpentine diffusion 近似实现，不是完整 Hilbert 曲线版本。
- 运行时间来自本机 Python 原型，不能直接代表生产性能。
