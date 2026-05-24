# Task C Prompt 工程草案

> 路线：ADR-005a，纯 API；不使用 GPU / ControlNet / IPAdapter。  
> 验收：只看量化输出图，不用 AI 原图直接评分。

## 写实人像（强约束）

```text
preserve exact facial features, identity, expression, and proportions of the input person.
only change the rendering style to clean N-bit pixel art suitable for perler bead patterns.
do not alter face shape, eye spacing, nose, mouth shape, or skin tone.
plain background, centered subject, 1024x1024.
```

变量：

- `N-bit`：8-bit / 16-bit / 24-bit 各跑一次，最终看量化后 ID 保持。
- 输出进入 Task B 推荐组合：K-means + CIEDE2000 + 无抖动。

## Q 版人像（弱约束）

```text
chibi cute cartoon version of the input person, big head, simplified features,
N-bit pixel art style. preserve hair color, skin tone, and general identity hints,
but allow stylized exaggeration. plain background, 1024x1024.
```

## 宠物

```text
turn the pet in the input image into clean pixel art suitable for perler bead patterns.
preserve species, fur color blocks, eye shape, nose position, and distinctive markings.
plain background, 1024x1024.
```

## 通用卡通

```text
convert the image into bold readable pixel art suitable for perler bead patterns.
preserve the main silhouette and color identity, simplify small details,
plain background, 1024x1024.
```

## Provider 映射

| Provider | 状态 | Prompt 处理 |
|----------|------|-------------|
| P1 `gpt-image-2` | 等 `XIAOCHI_GPT_API_KEY` | 使用上面的英文模板 |
| P2 即梦 | 等 `VOLC_ACCESS_KEY` / `VOLC_SECRET_KEY` | 需要补中文模板与 API 参数 |
| P3 通义万相 | 等 `ALIYUN_DASHSCOPE_API_KEY` | 需要补中文模板与 API 参数 |
