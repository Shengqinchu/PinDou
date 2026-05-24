# GitHub Landscape — 拼豆 / 像素化 / AI 工作流

> 调研日期：2026-05-24  
> 方法：公开 GitHub 页面 / API；未 fork、未下载模型权重。  
> 注：brief 中的 `WuhanLuxin/Pixelization` 公开访问为 404；论文公开页面指向的官方实现更接近 `WuZongWei6/Pixelization`。

| 仓库 | Star | 协议 | 技术 / 算法 | 对 PinDou 的价值 | 风险 |
|------|-----:|------|-------------|------------------|------|
| [WuZongWei6/Pixelization](https://github.com/WuZongWei6/Pixelization) | 418 | 非商业研究许可 | SIGGRAPH Asia 2022；alias-aware、cell-controllable pixelization；PyTorch | 高质量像素化思路：先结构提取再像素化 | 禁止未授权商用；依赖 GPU |
| [tencent-ailab/IP-Adapter](https://github.com/tencent-ailab/IP-Adapter) | 6.6k | Apache-2.0 | 图像提示适配器；参考图约束身份 / 风格 | 可参考“参考图 + 文本 prompt”的身份保持思路 | ADR-005a 当前不引入本地 GPU |
| [Comfy-Org/ComfyUI](https://github.com/Comfy-Org/ComfyUI) | 114k | GPL-3.0 | 节点式 diffusion workflow | 工作流拆分思路：去背景、风格化、量化可节点化 | GPL 商业化风险；不适合嵌入 |
| [AUTOMATIC1111/stable-diffusion-webui](https://github.com/AUTOMATIC1111/stable-diffusion-webui) | 163k | AGPL-3.0 | Gradio SD WebUI；LoRA / ControlNet 生态 | 观察 pixel-art LoRA、img2img 参数习惯 | AGPL 风险极高 |
| [lllyasviel/ControlNet](https://github.com/lllyasviel/ControlNet) | 33.9k | Apache-2.0 | 边缘 / 深度 / 姿态条件控制 | 人像转拼豆可保轮廓、姿态、五官结构 | 本地推理成本高；Task C 只作概念参考 |
| [Mikubill/sd-webui-controlnet](https://github.com/Mikubill/sd-webui-controlnet) | 17.9k | GPL-3.0 | A1111 ControlNet 扩展 | 观察社区组合和参数 | GPL；扩展生态易碎 |
| [cubiq/ComfyUI_IPAdapter_plus](https://github.com/cubiq/ComfyUI_IPAdapter_plus) | 6.0k | GPL-3.0 | ComfyUI IPAdapter 节点 | “一张参考图控制身份”适合人像保真 | 维护状态 / GPL / 模型依赖 |
| [sedthh/pyxelate](https://github.com/sedthh/pyxelate) | 1.7k | MIT | Python；palette transfer；dithering | 可复用低分辨率 + 调色板迁移 + 抖动思路 | 输出偏数字像素画，需再映射真实豆色 |
| [Tezumie/Image-to-Pixel](https://github.com/Tezumie/Image-to-Pixel) | 286 | MIT / Apache | JS；Floyd-Steinberg / Bayer / Atkinson；自定义 palette | 前端实时预览、抖动强度、Lospec palette 体验好 | 色板不是拼豆专用 |
| [ImageOptim/libimagequant](https://github.com/ImageOptim/libimagequant) | 910 | GPL / commercial dual | Rust / C；高质量 palette quantization | 可作量化质量基准 | 闭源商用需商业授权 |
| [gametorch/image_to_pixel_art_wasm](https://github.com/gametorch/image_to_pixel_art_wasm) | 169 | MIT | Rust WASM；K-means；浏览器端运行 | MVP 前端本地量化候选，隐私好、部署轻 | K-means 对肤色 / 渐变需配合 ΔE |
| [maxcleme/beadifier](https://github.com/maxcleme/beadifier) | 59 | MIT | Angular；图片转 bead pattern；PDF 导出 | 拼豆专用 UX：品牌、豆板、用量、PDF | 色卡来源需核验 |
| [Jett-Wu/Perler_Beads_Generator](https://github.com/Jett-Wu/Perler_Beads_Generator) | 1 | MIT | TypeScript；中文拼豆图纸编辑器 | 中文用户交互 / 图纸编辑可参考 | 新仓库，成熟度低 |
| [sucpyy/perler-pattern](https://github.com/sucpyy/perler-pattern) | 2 | MIT | Python；图片转拼豆图纸 | 轻量脚本参考 | 生态小，需读源码后再评估 |

## Top 3 可复用候选

1. [gametorch/image_to_pixel_art_wasm](https://github.com/gametorch/image_to_pixel_art_wasm)：MIT，Rust/WASM，适合前端本地 K-means 量化 MVP。
2. [Tezumie/Image-to-Pixel](https://github.com/Tezumie/Image-to-Pixel)：MIT / Apache，JS，抖动算法和实时预览交互可参考。
3. [sedthh/pyxelate](https://github.com/sedthh/pyxelate)：MIT，palette transfer + dithering，适合继续做算法对照。

`libimagequant` 效果强，但 GPL / commercial dual license，适合作基准，不建议直接集成闭源产品。
