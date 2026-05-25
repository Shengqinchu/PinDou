"""PatternBuilder contract from PRD v1.0 section 5.2."""

from __future__ import annotations

from dataclasses import dataclass, field

from pindou.providers.base import SizePreset


@dataclass(frozen=True)
class NoBead:
    reason: str = "transparent"


@dataclass(frozen=True)
class ColorRef:
    brand: str
    code: str
    name_cn: str
    name_en: str | None
    hex: str
    rgb: tuple[int, int, int]
    bead_diameter_mm: float


@dataclass(frozen=True)
class PatternSheet:
    grid: list[list[ColorRef | NoBead]]
    color_counts: dict[str, int]
    bead_total: int
    coords: list[tuple[int, int, str]]
    no_bead_mask: list[list[bool]]
    palette_used: list[ColorRef]
    estimated_cost_cny: float
    brand: str
    bead_diameter_mm: float
    suggested_buffer_pct: int = 10
    metadata: dict = field(default_factory=dict)


class PatternBuilder:
    def build(
        self,
        size: SizePreset,
        preview: bytes | None = None,
        raw_image: bytes | None = None,
        brand: str = "MARD",
        bead_diameter_mm: float = 5.0,
        mode: str = "auto",
    ) -> PatternSheet:
        raise NotImplementedError
