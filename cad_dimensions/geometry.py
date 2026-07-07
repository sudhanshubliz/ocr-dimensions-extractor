from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class BBox:
    x0: int
    y0: int
    x1: int
    y1: int

    @property
    def width(self) -> int:
        return max(0, self.x1 - self.x0)

    @property
    def height(self) -> int:
        return max(0, self.y1 - self.y0)

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2

    def intersects(self, other: "BBox") -> bool:
        return not (self.x1 <= other.x0 or self.x0 >= other.x1 or self.y1 <= other.y0 or self.y0 >= other.y1)

    def contains_point(self, x: float, y: float) -> bool:
        return self.x0 <= x <= self.x1 and self.y0 <= y <= self.y1

    def expand(self, pad: int, max_width: int, max_height: int) -> "BBox":
        return BBox(
            max(0, self.x0 - pad),
            max(0, self.y0 - pad),
            min(max_width, self.x1 + pad),
            min(max_height, self.y1 + pad),
        )

    def to_dict(self) -> dict:
        return {"x0": self.x0, "y0": self.y0, "x1": self.x1, "y1": self.y1}


@dataclass(frozen=True)
class ExclusionRegion:
    name: str
    bbox: BBox


def any_intersection(bbox: BBox | None, regions: Iterable[ExclusionRegion]) -> str | None:
    if bbox is None:
        return None
    for region in regions:
        if bbox.intersects(region.bbox):
            return region.name
    return None
