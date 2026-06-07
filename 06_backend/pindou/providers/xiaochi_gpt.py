"""Xiaochi GPT image provider."""

from __future__ import annotations

import base64
import hashlib
import io
import random
import time
import urllib.request
from collections.abc import Callable
from typing import Any

from openai import OpenAI
from PIL import Image

from pindou.config import get_settings
from pindou.pattern.postprocess import detect_and_remove_white_bg
from pindou.providers.base import PreviewProvider, PreviewProviderError, PreviewResult, SizePreset, StylePreset


TARGET_COLOR_COUNT = 6
IMAGE_SIZE = "1024x1024"
PROMPT_VARIANT_A = "prompt_a_current"
PROMPT_VARIANT_B = "prompt_b_grid_symmetry_20260606"
PROMPT_VERSION_BY_VARIANT = {
    PROMPT_VARIANT_A: "2026-06-01",
    PROMPT_VARIANT_B: "2026-06-06",
}

BEAD_OPTIMIZED_CHIBI_PROMPT = """
把上传照片变成可爱 Q 版(chibi)卡通贴纸，用于转拼豆图纸：
- 先自动识别画面真实主体(人/宠物/物体)，按真实主体萌化；即使与所选风格不符，也以真实主体为准(明显是人就出人，不要出成动物)。【静默执行，不向用户提示】
- 用尽量少的平涂色，通常 3-6 种，简单主体更少；不要渐变、不要细碎纹理。
- 粗而干净的黑色描边；背景透明或纯色；主体居中占画面大。
- 保留关键特征(眼睛/嘴/显著花纹)与辨识度；尽量左右对称、形状干净。
- 风格：温暖可爱、韩系手绘贴纸感。
""".strip()

BEAD_OPTIMIZED_CHIBI_PROMPT_B = """
把上传照片变成可爱 Q 版(chibi)卡通贴纸，用于转拼豆图纸：

主体与防呆：
- 先自动识别画面真实主体(人/宠物/物体)，按真实主体萌化；即使与所选风格不符，也以真实主体为准(明显是人就出人，不要出成动物)。【静默执行，不向用户提示】
- 主体居中，占画面大但不要贴边；四周保留清晰安全边距，方便后续裁成拼豆板网格。
- 输出为正面/正交视角，避免透视、倾斜角度、3D 渲染、强光影和镜头效果。

拼豆友好画法：
- 使用平涂、硬边、干净色块；不要照片质感、柔边、笔刷纹理、渐变、噪点或细碎材质。
- 控制颜色数量，通常 3-6 种；简单主体更少。避免大量相近色；阴影最多用 2-4 个相邻色阶表达，不要细腻渐变。
- 用深色或黑色拼豆感描边强化外轮廓，让主体缩小或远看时仍清晰可读。
- 眼睛、嘴巴、表情、手、显著花纹、道具等关键特征必须保留，并画得足够大、足够干净，以便低分辨率量化后仍能存活。
- 形状尽量左右对称、轮廓圆润、边缘干净。

风格：
- 温暖可爱、韩系手绘贴纸感，适合转成实体拼豆图纸。
""".strip()

PROMPTS_BY_VARIANT = {
    PROMPT_VARIANT_A: BEAD_OPTIMIZED_CHIBI_PROMPT,
    PROMPT_VARIANT_B: BEAD_OPTIMIZED_CHIBI_PROMPT_B,
}

STYLE_HINTS: dict[StylePreset, str] = {
    StylePreset.Q_PORTRAIT: "人像提示：如果真实主体是人，请重点保留发型、眼镜、脸部朝向、衣服主色和标志性配饰。",
    StylePreset.Q_COUPLE: "卡通提示：如果真实主体本来就是卡通/插画，请保留原角色轮廓、表情和主要配色，继续做成干净 Q 版贴纸。",
    StylePreset.Q_PET: "萌宠提示：如果真实主体是宠物，请重点保留物种、耳朵、眼鼻位置、显著花纹和表情。",
    StylePreset.CARTOON_FALLBACK: "普通卡通提示：保留真实主体数量、姿势、主体轮廓和关键特征，避免增加无关道具。",
}

PERLER_NEGATIVE_CONSTRAINTS = """
Hard negative constraints:
- Do not preserve photographic fur strands, skin pores, fabric texture, bokeh, lens blur, realistic highlights, or tonal gradients.
- Do not use painterly shading, airbrush lighting, semi-transparent shadows, tiny texture strokes, or anti-aliased fuzzy edges.
- Do not create extra colors for shadows; if a shadow is unavoidable, replace it with one flat darker solid color.
- Prefer 3-6 total flat colors; simple subjects should use only 3-4 colors when possible.
- Every colored region must be simple enough to become one or more perler bead cells.
- Output should look like a finished bead-pattern preview, not a realistic cartoon portrait.
- No perspective view, tilted camera, 3D render, dramatic lighting, or realistic material rendering.
- Keep facial features and important props large enough to survive a low-resolution bead-grid quantization.
""".strip()


class XiaochiGptProvider(PreviewProvider):
    """Generate Q-version finished previews through the OpenAI-compatible proxy."""

    name = "xiaochi_gpt_image_2"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        client: Any | None = None,
        timeout_seconds: float = 300.0,
        retry_count: int = 1,
        seed_factory: Callable[[], int] | None = None,
        enable_white_bg_auto_nobead: bool | None = None,
        prompt_variant: str | None = None,
    ) -> None:
        settings = get_settings()
        secret = settings.xiaochi_gpt_api_key
        resolved_api_key = api_key or (secret.get_secret_value() if secret else None)
        self.base_url = (base_url or settings.xiaochi_gpt_base_url).rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.retry_count = retry_count
        self.image_cost_cny = settings.xiaochi_gpt_image_cost_cny
        self.prompt_variant = normalize_prompt_variant(prompt_variant or settings.xiaochi_gpt_prompt_variant)
        self.enable_white_bg_auto_nobead = (
            settings.enable_ai_preview_white_bg_auto_nobead
            if enable_white_bg_auto_nobead is None
            else enable_white_bg_auto_nobead
        )
        self.seed_factory = seed_factory or (lambda: random.SystemRandom().randint(1, 2_147_483_647))

        if client is not None:
            self._client = client
            return
        if not resolved_api_key:
            raise PreviewProviderError("XIAOCHI_GPT_API_KEY is not configured.")
        self._client = OpenAI(
            api_key=resolved_api_key,
            base_url=self.base_url,
            timeout=timeout_seconds,
        )

    def generate(
        self,
        image: bytes,
        style_preset: StylePreset,
        size_preset: SizePreset,
        seed: int | None = None,
    ) -> PreviewResult:
        started = time.perf_counter()
        last_error: Exception | None = None
        attempts = self.retry_count + 1
        for attempt_index in range(attempts):
            attempt_seed = seed if attempt_index == 0 else self.seed_factory()
            prompt = self._build_prompt(style_preset, size_preset, attempt_seed)
            prompt_hash = prompt_digest(prompt)
            try:
                preview = self._edit_image(image, prompt)
                preview, white_bg_detected = self._auto_strip_white_bg(preview)
                return PreviewResult.from_image_bytes(
                    preview,
                    target_color_count=TARGET_COLOR_COUNT,
                    provider_used=self.name,
                    fallback_count=0,
                    cost_estimate=self.image_cost_cny,
                    latency_ms=round((time.perf_counter() - started) * 1000),
                    metadata={
                        "model": "gpt-image-2",
                        "style_preset": style_preset.value,
                        "size_preset": size_preset.value,
                        "attempts": attempt_index + 1,
                        "seed": attempt_seed,
                        "prompt_variant": self.prompt_variant,
                        "prompt_version": PROMPT_VERSION_BY_VARIANT[self.prompt_variant],
                        "prompt_hash": prompt_hash,
                        "white_bg_auto_nobead_enabled": self.enable_white_bg_auto_nobead,
                        "white_bg_detected": white_bg_detected,
                    },
                )
            except Exception as exc:  # noqa: BLE001 - provider boundary normalizes failures.
                last_error = exc
        raise PreviewProviderError(f"{self.name} failed after {attempts} attempt(s): {last_error}") from last_error

    def _build_prompt(self, style_preset: StylePreset, size_preset: SizePreset, seed: int | None) -> str:
        try:
            style_hint = STYLE_HINTS[style_preset]
        except KeyError as exc:
            raise PreviewProviderError(f"Unsupported style preset: {style_preset}") from exc
        return "\n\n".join(
            [
                PROMPTS_BY_VARIANT[self.prompt_variant],
                f"所选风格提示（仅作参考，真实主体识别优先，静默纠偏）：{style_hint}",
                PERLER_NEGATIVE_CONSTRAINTS,
                f"Output canvas: {IMAGE_SIZE}. Target bead grid preset: {size_preset.value}.",
                "Return only the final finished-preview image, no text overlays.",
                f"Seed hint: {seed}" if seed is not None else "Seed hint: provider default.",
            ]
        )

    def _edit_image(self, image: bytes, prompt: str) -> bytes:
        image_file = io.BytesIO(image)
        image_file.name = "input.png"
        response = self._client.images.edit(
            model="gpt-image-2",
            image=image_file,
            prompt=prompt,
            size=IMAGE_SIZE,
            response_format="b64_json",
        )
        return self._extract_image_bytes(response)

    def _extract_image_bytes(self, response: Any) -> bytes:
        data = self._get(response, "data")
        if not data:
            raise PreviewProviderError("Image API response has no data items.")
        item = data[0]
        encoded = self._get(item, "b64_json")
        if encoded:
            return base64.b64decode(encoded)
        url = self._get(item, "url")
        if url:
            request = urllib.request.Request(url, headers={"User-Agent": "PinDou/0.1"})
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                return response.read()
        raise PreviewProviderError("Image API response has neither b64_json nor url.")

    def _auto_strip_white_bg(self, image: bytes) -> tuple[bytes, bool]:
        if not self.enable_white_bg_auto_nobead:
            return image, False
        try:
            source = Image.open(io.BytesIO(image)).convert("RGBA")
            if min(source.size) < 8:
                return image, False
            processed, detected = detect_and_remove_white_bg(source)
            if not detected:
                return image, False
            output = io.BytesIO()
            processed.save(output, format="PNG")
            return output.getvalue(), True
        except Exception:
            return image, False

    @staticmethod
    def _get(value: Any, key: str) -> Any:
        if isinstance(value, dict):
            return value.get(key)
        return getattr(value, key, None)


def normalize_prompt_variant(raw: str) -> str:
    normalized = (raw or PROMPT_VARIANT_A).strip().lower()
    aliases = {
        "a": PROMPT_VARIANT_A,
        "current": PROMPT_VARIANT_A,
        "prompt_a": PROMPT_VARIANT_A,
        PROMPT_VARIANT_A: PROMPT_VARIANT_A,
        "b": PROMPT_VARIANT_B,
        "prompt_b": PROMPT_VARIANT_B,
        "grid_symmetry": PROMPT_VARIANT_B,
        PROMPT_VARIANT_B: PROMPT_VARIANT_B,
    }
    return aliases.get(normalized, PROMPT_VARIANT_A)


def prompt_digest(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:12]
