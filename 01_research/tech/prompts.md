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

旧模板只适合初步测试，容易让模型自动补全身体。真实用户素材改用下面的拼豆约束模板。

```text
chibi cute cartoon version of the input person, big head, simplified features,
N-bit pixel art style. preserve hair color, skin tone, and general identity hints,
but allow stylized exaggeration. plain background, 1024x1024.
```

## Q 版人像（拼豆成品预览约束模板）

```text
Transform the uploaded photo into a cute Q-version chibi illustration for a perler bead finished-product preview.

Strict composition rules:
- Preserve the original visible body range and pose.
- Do not invent missing body parts.
- If legs, feet, shoes, or the full lower body are not visible in the original photo, do not generate them.
- Keep the subject as a waist-up / upper-body composition if the original is waist-up.
- Do not change the number of people.
- Do not add extra pets, props, text, logos, or decorative objects.

Preserve identity and key details:
- Preserve hairstyle, glasses, face direction, clothing type and main colors, accessories, hand-held objects, and the relationship between subjects.
- For graduation photos, preserve graduation cap, black gown, collar trim color, bouquet, and glasses if visible.
- Remove background clutter, cars, license plates, text, and watermarks.

Perler bead design style:
- Thick black outline.
- Large clean color blocks.
- Minimal shadows and gradients.
- Simple cute facial features.
- Plain white or transparent-looking background; background should not be part of the bead design.
- Suitable for later conversion into a 60x80, 80x100, or 100x120 bead grid.
- Target 12-18 solid colors, maximum 24 colors.
```

中文业务含义：

- AI 产物先服务“成品展示图”，不是严肃图纸。
- 严肃图纸由程序根据量化结果生成：网格、色号、颗粒数量、分区、PDF / Excel。
- `big head, small body` 必须受“原图可见范围”约束，否则会补腿补脚。

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

## 直接拼豆预览（仅展示，不作为严肃图纸）

```text
Create a perler bead finished-product preview based on the uploaded image.
Keep the original subject count, visible body range, pose, and key accessories.
Do not invent missing body parts or extra props.
Use round bead-like dots, clean black outlines, large readable color blocks, and a plain white background.
Keep the design centered and suitable for a 60x80 or 80x100 grid.
Do not draw fake color legends, fake coordinates, or unreadable text.
```

说明：此模板适合快速验证“用户看了想不想买”。最终图纸仍走程序化量化和导出。

## Provider 映射

| Provider | 状态 | Prompt 处理 |
|----------|------|-------------|
| P1 `gpt-image-2` | 等 `XIAOCHI_GPT_API_KEY` | 使用上面的英文模板 |
| P2 即梦 | 等 `VOLC_ACCESS_KEY` / `VOLC_SECRET_KEY` | 需要补中文模板与 API 参数 |
| P3 通义万相 | 等 `ALIYUN_DASHSCOPE_API_KEY` | 需要补中文模板与 API 参数 |
