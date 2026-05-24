# Task B — 算法方案横评

**Status**: completed (Codex @ 2026-05-24) — 产出：[algorithms.md](../../01_research/tech/algorithms.md), [algorithm_metrics.csv](../../01_research/tech/algorithm_metrics.csv), [algorithm_impls](../../01_research/tech/algorithm_impls/), [algorithm_samples](../../01_research/tech/algorithm_samples/)
**Owner**: Codex
**Priority**: 高
**Estimated**: 2-3 天
**依赖**: 任务 D 色卡数据库（量化用 MARD/COCO 色卡作 palette）

---

## 背景
拼豆图纸的核心是"把任意图片量化到色卡的有限色彩域"。算法选错的后果：脚本量化效果差，AI 预处理白做。本任务给 Phase 1 PRD 锁定算法路线提供数据。

## 目标
在**同一组测试图**上跑全部组合，输出客观指标 + 主观对比图，给出"按风格预设的推荐组合"。

## 三个维度的算法

### 维度 1：颜色量化
- K-means（scikit-learn 标准实现）
- Median-cut（PIL/Pillow `quantize(method=Image.MEDIANCUT)`）
- Octree（Pillow `quantize(method=Image.FASTOCTREE)`）
- Neural Color Quantization（参考论文 DeepPalette / ColorQuantNet，若开源实现可用）

### 维度 2：色差度量（决定"哪个色卡颜色最接近"）
- RGB Euclidean（最快，最差）
- CIE76（CIELAB 欧氏距离）
- CIE94
- **CIEDE2000**（最准，工业标准）

### 维度 3：抖动算法
- 无抖动（baseline）
- Floyd-Steinberg
- Atkinson
- Bayer（有序抖动 / 矩阵抖动）
- Riemersma（Hilbert 曲线）

总组合数 = 4 × 4 × 5 = 80。**不需要跑全 80 个**，挑代表性组合（详见下方矩阵）。

---

## 任务步骤

### 步骤 1：建测试集
固定 3 张图：1 人像 + 1 宠物 + 1 卡通（与任务 A、C 共用同一组测试图，存到 `01_research/tech/test_inputs/`）。

### 步骤 2：用 Python 实现每种算法
- 输入：3 张测试图
- Palette：MARD 色卡（任务 D 输出的 `01_research/colormap/mard.json`）
- 输出分辨率：100×100 像素

每种算法给出一份 **可独立运行的 Python 脚本** 存到 `01_research/tech/algorithm_impls/`：
- `quantize_kmeans.py`
- `quantize_median_cut.py`
- `quantize_octree.py`
- `quantize_neural.py`（如可行）
- `colordiff_*.py` —— 提取为 utility
- `dither_*.py` —— 提取为 utility

### 步骤 3：跑代表性组合
**Phase 1（先跑 12 组）**：
| 组合 ID | 量化 | 色差 | 抖动 |
|---------|------|------|------|
| C01 | K-means | RGB | 无 |
| C02 | K-means | CIEDE2000 | 无 |
| C03 | K-means | CIEDE2000 | Floyd-Steinberg |
| C04 | Median-cut | CIEDE2000 | Floyd-Steinberg |
| C05 | Octree | CIEDE2000 | Floyd-Steinberg |
| C06 | K-means | CIEDE2000 | Atkinson |
| C07 | K-means | CIEDE2000 | Bayer |
| C08 | K-means | CIEDE2000 | Riemersma |
| C09 | K-means | CIE94 | Floyd-Steinberg |
| C10 | K-means | CIE76 | Floyd-Steinberg |
| C11 | Neural | CIEDE2000 | Floyd-Steinberg |
| C12 | K-means | CIEDE2000 | 无（对照） |

**Phase 2（按 Phase 1 结果再补充 5-8 组）**。

### 步骤 4：客观指标
对每组输出图，计算：
- **PSNR**（峰值信噪比，对比原图）
- **SSIM**（结构相似度，对比原图）
- **CIEDE2000 平均色差**（对比原图）
- **运行时间**（毫秒）

存到 `01_research/tech/algorithm_metrics.csv`。

### 步骤 5：主观对比图
把每组输出图按 3×4 拼成对比图（行 = 测试图，列 = 组合 ID），存到 `01_research/tech/algorithm_samples/`：
- `compare_portrait.png`
- `compare_pet.png`
- `compare_cartoon.png`

### 步骤 6：写报告
- 每种算法给一段："适合场景 / 不适合场景"
- 每个测试图给一段："最佳组合是哪个 / 为什么"
- 按风格预设给推荐：写实人像推荐 X、Q 版推荐 Y、宠物推荐 Z、卡通推荐 W

---

## 输出位置
- 主报告：`01_research/tech/algorithms.md`
- 实现代码：`01_research/tech/algorithm_impls/`
- 对比图：`01_research/tech/algorithm_samples/`
- 客观指标 CSV：`01_research/tech/algorithm_metrics.csv`

## 验收标准
- [ ] 至少 12 个组合的实测数据（CSV）
- [ ] 3 张主观对比图
- [ ] 每种算法都有可独立运行的 Python 实现
- [ ] 报告末尾给出"按风格预设的推荐组合"
- [ ] 至少识别 1 个反直觉发现（如"Floyd-Steinberg 在某场景反而不如 Atkinson"）
- [ ] 实现代码全部走相对路径 / 配置驱动，没有硬编码 key

## 不要做
- 不要做 AI 预处理（任务 C）
- 不要预先优化（先跑完，再回头优化运行时间）
- 不要用商业 API 替代算法（这里是脚本量化基线）
