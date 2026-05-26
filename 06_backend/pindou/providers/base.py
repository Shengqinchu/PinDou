"""PreviewProvider contracts.

The public enum values mirror ``05_frontend/api/index.ts``. The provider keeps
the raw image bytes internally so the later API layer can persist them and fill
the frontend-facing ``image_url``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import math
from enum import StrEnum
from typing import Any
from uuid import uuid4


class StylePreset(StrEnum):
    Q_PORTRAIT = "q_portrait"
    Q_PET = "q_pet"
    Q_COUPLE = "q_couple"
    CARTOON_FALLBACK = "cartoon_fallback"


class SizePreset(str):
    """Validated bead grid size in ``{width}x{height}`` form.

    Preset constants remain available for code/tests, while the constructor
    also accepts custom integer sizes within the product guardrails.
    """

    MIN_DIMENSION = 20
    MAX_DIMENSION = 200
    MIN_ASPECT_RATIO = 0.5
    MAX_ASPECT_RATIO = 2.0
    BOARD_INTERVAL = 26
    PRESET_VALUES = {"26x26", "52x52", "78x78", "104x104"}

    def __new__(cls, value: str) -> "SizePreset":
        normalized, width, height = parse_size_value(value)
        validate_size_value(width, height)
        obj = str.__new__(cls, normalized)
        obj._width = width
        obj._height = height
        obj._is_preset = normalized in cls.PRESET_VALUES
        obj._warning = board_alignment_warning(width, height)
        return obj

    @property
    def value(self) -> str:
        return str(self)

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    @property
    def is_preset(self) -> bool:
        return self._is_preset

    @property
    def warning(self) -> str | None:
        return self._warning


def parse_size_value(value: str) -> tuple[str, int, int]:
    normalized = str(value).strip().lower().replace("×", "x")
    parts = normalized.split("x", 1)
    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
        raise ValueError("Size must use integer WIDTHxHEIGHT format, such as 52x52.")
    width = int(parts[0])
    height = int(parts[1])
    return f"{width}x{height}", width, height


def validate_size_value(width: int, height: int) -> None:
    if width < SizePreset.MIN_DIMENSION or height < SizePreset.MIN_DIMENSION:
        raise ValueError("Size must be at least 20x20.")
    if width > SizePreset.MAX_DIMENSION or height > SizePreset.MAX_DIMENSION:
        raise ValueError("Size must be at most 200x200.")
    aspect_ratio = width / height
    if aspect_ratio < SizePreset.MIN_ASPECT_RATIO or aspect_ratio > SizePreset.MAX_ASPECT_RATIO:
        raise ValueError("Size aspect ratio must be between 0.5 and 2.0.")


def board_alignment_warning(width: int, height: int) -> str | None:
    interval = SizePreset.BOARD_INTERVAL
    if width % interval == 0 and height % interval == 0:
        return None
    boards_w = math.ceil(width / interval)
    boards_h = math.ceil(height / interval)
    total_boards = boards_w * boards_h
    return f"不对齐 26 格拼豆板，建议准备约 {boards_w}×{boards_h} 块板（共 {total_boards} 块）后裁边。"


SizePreset.SINGLE_BOARD_26X26 = SizePreset("26x26")  # type: ignore[attr-defined]
SizePreset.DOUBLE_BOARD_52X52 = SizePreset("52x52")  # type: ignore[attr-defined]
SizePreset.TRIPLE_BOARD_78X78 = SizePreset("78x78")  # type: ignore[attr-defined]
SizePreset.FOUR_BOARD_104X104 = SizePreset("104x104")  # type: ignore[attr-defined]


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
