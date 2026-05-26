"""Xiaochi GPT image provider."""

from __future__ import annotations

import base64
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


TARGET_COLOR_COUNT = 8
IMAGE_SIZE = "1024x1024"

STYLE_PROMPTS: dict[StylePreset, str] = {
    StylePreset.Q_PORTRAIT: """
Transform the uploaded photo into a cute Q-version chibi illustration for a perler bead finished-product preview.

Strict composition rules:
- Preserve the original visible body range and pose.
- Do not invent missing body parts.
- If legs, feet, shoes, or the full lower body are not visible in the original photo, do not generate them.
- Keep the subject as a waist-up / upper-body composition if the original is waist-up.
- Do not change the number of people.
- Do not add extra pets, props, text, logos, or decorative objects.

Preserve identity and key details:
- Preserve hairstyle, glasses, face direction, clothing type and main colors, accessories, and hand-held objects.
- Remove background clutter, license plates, text, and watermarks.

Perler bead design style:
- Hand-drawn perler bead pattern style, like children's coloring book line art.
- Thick 3-5 pixel solid black outline on every subject edge and major internal feature.
- Large clean flat solid color blocks.
- Simple cute facial features.
- Use ONLY 5-8 solid colors total.
- No fur texture, no realistic shading, no photo realism, no gradients, no anti-aliasing, no soft shadows.
- Plain white or transparent-looking background; background should not be part of the bead design.
- Suitable for later conversion into a small chibi bead grid.
""".strip(),
    StylePreset.Q_COUPLE: """
Transform the uploaded couple/group photo into a cute Q-version chibi illustration for a perler bead finished-product preview.

Strict composition rules:
- Keep the same number of people and preserve their left/right relationship.
- Preserve the original visible body range and pose for each person.
- Do not invent missing body parts; if the lower body is not visible, keep the result upper-body only.
- Do not add extra pets, props, text, logos, or decorative objects.

Preserve identity and key details:
- Preserve each person's hairstyle, glasses, face direction, clothing type and main colors, accessories, hand-held objects, and relative height impression.
- For graduation photos, preserve graduation caps, black gowns, collar trim colors, bouquet, and glasses if visible.
- Remove background clutter, cars, license plates, text, and watermarks.

Perler bead design style:
- Hand-drawn perler bead pattern style, like children's coloring book line art.
- Thick 3-5 pixel solid black outline on every subject edge and major internal feature.
- Large clean flat solid color blocks.
- Simple cute facial features.
- Use ONLY 5-8 solid colors total.
- No fur texture, no realistic shading, no photo realism, no gradients, no anti-aliasing, no soft shadows.
- Plain white or transparent-looking background; background should not be part of the bead design.
- Suitable for later conversion into a small chibi bead grid.
""".strip(),
    StylePreset.Q_PET: """
Transform the uploaded pet photo into a cute Q-version chibi pet illustration for a perler bead finished-product preview.

Strict composition rules:
- Preserve the pet species, pose, visible body range, and main silhouette.
- Do not invent missing legs, tail, collar, accessories, props, or extra pets.
- Keep distinctive ears, eye shape, nose position, fur markings, and expression.
- Remove background clutter, text, logos, and watermarks.

Perler bead design style:
- Hand-drawn perler bead pattern style, like children's coloring book line art.
- Thick 3-5 pixel solid black outline on every subject edge and major internal feature.
- Large clean flat solid color blocks.
- Simple cute facial features while keeping the pet recognizable.
- Use ONLY 5-8 solid colors total.
- No fur texture, no realistic shading, no photo realism, no gradients, no anti-aliasing, no soft shadows.
- Plain white or transparent-looking background; background should not be part of the bead design.
- Suitable for later conversion into a small chibi bead grid.
""".strip(),
    StylePreset.CARTOON_FALLBACK: """
Create a perler bead finished-product preview based on the uploaded image.

Keep the original subject count, visible body range, pose, main silhouette, and key accessories.
Do not invent missing body parts, extra props, text, logos, decorative objects, fake legends, or fake coordinates.
Use round bead-like dots, clean black outlines, large readable color blocks, and a plain white or transparent-looking background.
Use hand-drawn perler bead pattern style, like children's coloring book line art.
Use ONLY 5-8 solid colors total.
Use thick 3-5 pixel solid black outlines.
No fur texture, no realistic shading, no photo realism, no gradients, no anti-aliasing, no soft shadows.
Keep the design centered and suitable for a small chibi bead grid.
""".strip(),
}

PERLER_NEGATIVE_CONSTRAINTS = """
Hard negative constraints:
- Do not preserve photographic fur strands, skin pores, fabric texture, bokeh, lens blur, realistic highlights, or tonal gradients.
- Do not use painterly shading, airbrush lighting, semi-transparent shadows, tiny texture strokes, or anti-aliased fuzzy edges.
- Do not create extra colors for shadows; if a shadow is unavoidable, replace it with one flat darker solid color.
- Every colored region must be simple enough to become one or more perler bead cells.
- Output should look like a finished bead-pattern preview, not a realistic cartoon portrait.
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
        timeout_seconds: float = 90.0,
        retry_count: int = 1,
        seed_factory: Callable[[], int] | None = None,
        enable_white_bg_auto_nobead: bool | None = None,
    ) -> None:
        settings = get_settings()
        secret = settings.xiaochi_gpt_api_key
        resolved_api_key = api_key or (secret.get_secret_value() if secret else None)
        self.base_url = (base_url or settings.xiaochi_gpt_base_url).rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.retry_count = retry_count
        self.image_cost_cny = settings.xiaochi_gpt_image_cost_cny
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
                        "white_bg_auto_nobead_enabled": self.enable_white_bg_auto_nobead,
                        "white_bg_detected": white_bg_detected,
                    },
                )
            except Exception as exc:  # noqa: BLE001 - provider boundary normalizes failures.
                last_error = exc
        raise PreviewProviderError(f"{self.name} failed after {attempts} attempt(s): {last_error}") from last_error

    def _build_prompt(self, style_preset: StylePreset, size_preset: SizePreset, seed: int | None) -> str:
        try:
            prompt = STYLE_PROMPTS[style_preset]
        except KeyError as exc:
            raise PreviewProviderError(f"Unsupported style preset: {style_preset}") from exc
        return "\n\n".join(
            [
                prompt,
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
