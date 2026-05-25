"""Pattern export contract placeholder."""

from __future__ import annotations

from pindou.pattern.builder import PatternSheet


class PatternExporter:
    def to_simple_grid_png(self, pattern: PatternSheet) -> bytes:
        raise NotImplementedError

    def to_pdf(self, pattern: PatternSheet) -> bytes:
        raise NotImplementedError

    def to_excel(self, pattern: PatternSheet) -> bytes:
        raise NotImplementedError

    def to_partition_images(self, pattern: PatternSheet, block_size: int = 20) -> list[bytes]:
        raise NotImplementedError
