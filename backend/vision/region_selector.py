from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ScreenRegion:
    x: int
    y: int
    width: int
    height: int

    def as_bbox(self) -> tuple[int, int, int, int]:
        return self.x, self.y, self.width, self.height
