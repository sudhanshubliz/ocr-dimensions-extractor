from __future__ import annotations

from pathlib import Path

import cv2

from .geometry import BBox


def write_crop(image_path: Path, bbox: BBox | None, output_dir: Path, crop_id: str, pad: int = 16) -> str | None:
    if bbox is None:
        return None
    image = cv2.imread(str(image_path))
    if image is None:
        return None
    height, width = image.shape[:2]
    crop_box = bbox.expand(pad, width, height)
    crop = image[crop_box.y0 : crop_box.y1, crop_box.x0 : crop_box.x1]
    if crop.size == 0:
        return None
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{crop_id}.png"
    cv2.imwrite(str(output_path), crop)
    return str(output_path)
