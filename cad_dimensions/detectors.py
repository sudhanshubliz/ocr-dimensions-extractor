from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from .backends import Detection, DetectorBackend
from .geometry import BBox, ExclusionRegion


def _overlap_ratio(a: BBox, b: BBox) -> float:
    x0 = max(a.x0, b.x0)
    y0 = max(a.y0, b.y0)
    x1 = min(a.x1, b.x1)
    y1 = min(a.y1, b.y1)
    if x1 <= x0 or y1 <= y0:
        return 0.0
    intersection = (x1 - x0) * (y1 - y0)
    smaller = max(1, min(a.width * a.height, b.width * b.height))
    return intersection / smaller


def _dedupe_boxes(boxes: list[BBox], threshold: float = 0.55) -> list[BBox]:
    out: list[BBox] = []
    for box in sorted(boxes, key=lambda item: (item.y0, item.x0, -(item.width * item.height))):
        if any(_overlap_ratio(box, existing) >= threshold for existing in out):
            continue
        out.append(box)
    return out


class GeometryTextRegionDetector(DetectorBackend):
    name = "geometry-text-region"
    version = "0.1"

    def __init__(self, exclusions: list[ExclusionRegion] | None = None, min_confidence: float = 0.35) -> None:
        self.exclusions = exclusions or []
        self.min_confidence = min_confidence

    def detect(self, image_path: Path) -> list[Detection]:
        gray = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
        if gray is None:
            return []

        height, width = gray.shape[:2]
        work = gray.copy()
        for region in self.exclusions:
            box = region.bbox
            cv2.rectangle(work, (box.x0, box.y0), (box.x1, box.y1), 255, thickness=-1)

        _, ink = cv2.threshold(work, 185, 255, cv2.THRESH_BINARY_INV)
        kernels = [
            cv2.getStructuringElement(cv2.MORPH_RECT, (19, 3)),
            cv2.getStructuringElement(cv2.MORPH_RECT, (3, 19)),
            cv2.getStructuringElement(cv2.MORPH_RECT, (9, 5)),
        ]

        boxes: list[BBox] = []
        for kernel in kernels:
            joined = cv2.morphologyEx(ink, cv2.MORPH_CLOSE, kernel, iterations=1)
            contours, _ = cv2.findContours(joined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                box = BBox(x, y, x + w, y + h)
                if not self._looks_like_text_region(box, ink, width, height):
                    continue
                boxes.append(box.expand(4, width, height))

        detections: list[Detection] = []
        for box in _dedupe_boxes(boxes):
            crop = ink[box.y0 : box.y1, box.x0 : box.x1]
            density = float(np.count_nonzero(crop)) / max(1, box.width * box.height)
            confidence = min(0.95, max(self.min_confidence, density * 4.0))
            detections.append(Detection(box, "dimension_text_candidate", confidence))
        return detections

    def _looks_like_text_region(self, box: BBox, ink: np.ndarray, width: int, height: int) -> bool:
        if box.width < 10 or box.height < 6:
            return False
        if box.width > width * 0.38 or box.height > height * 0.18:
            return False
        if box.width * box.height < 60:
            return False

        crop = ink[box.y0 : box.y1, box.x0 : box.x1]
        density = float(np.count_nonzero(crop)) / max(1, box.width * box.height)
        aspect = box.width / max(1, box.height)
        if density < 0.015 or density > 0.78:
            return False
        if aspect > 35 or aspect < 0.05:
            return False
        if box.width > width * 0.22 and density < 0.05:
            return False
        return True
