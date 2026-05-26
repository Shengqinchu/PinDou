"""PreviewProvider contracts.

The public enum values mirror ``05_frontend/api/index.ts``. The provider keeps
the raw image bytes internally so the later API layer can persist them and fill
the frontend-facing ``image_url``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from uuid import uuid4


class StylePreset(StrEnum):
    Q_PORTRAIT = "q_portrait"
    Q_PET = "q_pet"
    Q_COUPLE = "q_couple"
    CARTOON_FALLBACK = "cartoon_fallback"


class SizePreset(StrEnum):
    SINGLE_BOARD_26X26 = "26x26"
    DOUBLE_BOARD_52X52 = "52x52"
    TRIPLE_BOARD_78X78 = "78x78"
    FOUR_BOARD_104X104 = "104x104"


@dataclass(frozen=True)
class PreviewResult:
    preview_id: str
    image_url: str
    # Internal transport for provider/pattern layers; the HTTP API will expose
    # image_url instead of serializing raw bytes.
    image: bytes
    target_color_count: int
    provider_used: str
    fallback_count: int
    cost_estimate: float
    latency_ms: int
    image_format: str = "png"
    target_resolution: tuple[int, int] = (1024, 1024)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_image_bytes(
        cls,
        image: bytes,
        *,
        target_color_count: int,
        provider_used: str,
        cost_estimate: float,
        latency_ms: int,
        fallback_count: int = 0,
        preview_id: str | None = None,
        image_url: str | None = None,
        image_format: str = "png",
        target_resolution: tuple[int, int] = (1024, 1024),
        metadata: dict[str, Any] | None = None,
    ) -> "PreviewResult":
        generated_id = preview_id or uuid4().hex
        return cls(
            preview_id=generated_id,
            image_url=image_url or f"pindou-preview://{generated_id}.{image_format}",
            image=image,
            target_color_count=target_color_count,
            provider_used=provider_used,
            fallback_count=fallback_count,
            cost_estimate=cost_estimate,
            latency_ms=latency_ms,
            image_format=image_format,
            target_resolution=target_resolution,
            metadata=metadata or {},
        )

    def to_frontend_dict(self) -> dict[str, str | int | float]:
        return {
            "preview_id": self.preview_id,
            "image_url": self.image_url,
            "target_color_count": self.target_color_count,
            "provider_used": self.provider_used,
            "fallback_count": self.fallback_count,
            "cost_estimate": self.cost_estimate,
            "latency_ms": self.latency_ms,
        }


class PreviewProviderError(RuntimeError):
    """Raised when a preview provider cannot produce an image."""


class PreviewProvider(ABC):
    name = "preview_provider"

    @abstractmethod
    def generate(
        self,
        image: bytes,
        style_preset: StylePreset,
        size_preset: SizePreset,
        seed: int | None = None,
    ) -> PreviewResult:
        """Generate a finished-preview image or raise PreviewProviderError."""
