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

from pindou.config import get_settings
from pindou.providers.base import PreviewProvider, PreviewProviderError, PreviewResult, SizePreset, StylePreset


TARGET_COLOR_COUNT = 18
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
- Thick black outline.
- Large clean color blocks.
- Minimal shadows and gradients.
- Simple cute facial features.
- Plain white or transparent-looking background; background should not be part of the bead design.
- Suitable for later conversion into a 60x80, 80x100, or 100x120 bead grid.
- Target 12-18 solid colors, maximum 24 colors.
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
- Thick black outline.
- Large clean color blocks.
- Minimal shadows and gradients.
- Simple cute facial features.
- Plain white or transparent-looking background; background should not be part of the bead design.
- Suitable for later conversion into a 60x80, 80x100, or 100x120 bead grid.
- Target 12-18 solid colors, maximum 24 colors.
""".strip(),
    StylePreset.Q_PET: """
Transform the uploaded pet photo into a cute Q-version chibi pet illustration for a perler bead finished-product preview.

Strict composition rules:
- Preserve the pet species, pose, visible body range, and main silhouette.
- Do not invent missing legs, tail, collar, accessories, props, or extra pets.
- Keep distinctive ears, eye shape, nose position, fur markings, and expression.
- Remove background clutter, text, logos, and watermarks.

Perler bead design style:
- Thick black outline.
- Large clean color blocks.
- Minimal shadows and gradients.
- Simple cute facial features while keeping the pet recognizable.
- Plain white or transparent-looking background; background should not be part of the bead design.
- Suitable for later conversion into a 60x80, 80x100, or 100x120 bead grid.
- Target 12-18 solid colors, maximum 24 colors.
""".strip(),
    StylePreset.CARTOON_FALLBACK: """
Create a perler bead finished-product preview based on the uploaded image.

Keep the original subject count, visible body range, pose, main silhouette, and key accessories.
Do not invent missing body parts, extra props, text, logos, decorative objects, fake legends, or fake coordinates.
Use round bead-like dots, clean black outlines, large readable color blocks, and a plain white or transparent-looking background.
Keep the design centered and suitable for a 60x80 or 80x100 grid.
Target 12-18 solid colors, maximum 24 colors.
""".strip(),
}


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
    ) -> None:
        settings = get_settings()
        secret = settings.xiaochi_gpt_api_key
        resolved_api_key = api_key or (secret.get_secret_value() if secret else None)
        self.base_url = (base_url or settings.xiaochi_gpt_base_url).rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.retry_count = retry_count
        self.image_cost_cny = settings.xiaochi_gpt_image_cost_cny
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

    @staticmethod
    def _get(value: Any, key: str) -> Any:
        if isinstance(value, dict):
            return value.get(key)
        return getattr(value, key, None)
