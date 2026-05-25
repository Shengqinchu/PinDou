"""PreviewProvider contract from PRD v1.0 section 5.1."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class StylePreset(StrEnum):
    CHIBI_PORTRAIT = "chibi_portrait"
    CHIBI_PET = "chibi_pet"
    CHIBI_COUPLE = "chibi_couple"
    CARTOON = "cartoon"


class SizePreset(StrEnum):
    SMALL_60X80 = "60x80"
    MEDIUM_80X100 = "80x100"
    LARGE_100X120 = "100x120"


@dataclass(frozen=True)
class PreviewResult:
    image: bytes
    target_color_count: int
    provider_used: str
    cost_estimate: float
    latency_ms: int
    image_format: str = "png"
    target_resolution: tuple[int, int] = (1024, 1024)
    fallback_count: int = 0
    metadata: dict = field(default_factory=dict)


class PreviewProvider:
    def generate(
        self,
        image: bytes,
        style_preset: StylePreset,
        size_preset: SizePreset,
        seed: int | None = None,
    ) -> PreviewResult:
        raise NotImplementedError
