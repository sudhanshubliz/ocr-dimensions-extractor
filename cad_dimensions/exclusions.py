from __future__ import annotations

from pathlib import Path

import cv2

from .geometry import BBox, ExclusionRegion


def detect_exclusion_regions(image_path: Path) -> list[ExclusionRegion]:
    image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        return []
    height, width = image.shape[:2]
    return [
        ExclusionRegion("border_grid_labels", BBox(0, 0, width, int(height * 0.055))),
        ExclusionRegion("border_grid_labels", BBox(0, int(height * 0.945), width, height)),
        ExclusionRegion("border_grid_labels", BBox(0, 0, int(width * 0.04), height)),
        ExclusionRegion("border_grid_labels", BBox(int(width * 0.96), 0, width, height)),
        ExclusionRegion("title_block", BBox(int(width * 0.68), int(height * 0.78), width, height)),
        ExclusionRegion("notes_block", BBox(int(width * 0.62), int(height * 0.45), width, int(height * 0.82))),
    ]
