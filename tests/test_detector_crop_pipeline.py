from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from cad_dimensions.backends import OCRCandidate
from cad_dimensions.detectors import GeometryTextRegionDetector
from cad_dimensions.ocr import extract_detector_crop_rows


class FakeOCRBackend:
    name = "fake-region-ocr"
    version = "test"

    def recognize(self, image_path: Path, regions=None):
        return [OCRCandidate("12 +/-1", regions[0].bbox, 91)] if regions else []


def test_geometry_text_region_detector_finds_dimension_like_text(tmp_path: Path) -> None:
    image_path = tmp_path / "page.png"
    image = np.full((220, 360), 255, dtype=np.uint8)
    cv2.putText(image, "12 +/-1", (80, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.0, 0, 2)
    cv2.imwrite(str(image_path), image)

    detections = GeometryTextRegionDetector().detect(image_path)

    assert detections
    assert any(detection.bbox.width > 40 and detection.bbox.height > 15 for detection in detections)


def test_detector_crop_rows_parse_and_validate_candidates(tmp_path: Path, monkeypatch) -> None:
    image_path = tmp_path / "page.png"
    image = np.full((220, 360), 255, dtype=np.uint8)
    cv2.putText(image, "12 +/-1", (80, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.0, 0, 2)
    cv2.imwrite(str(image_path), image)

    monkeypatch.setattr("cad_dimensions.ocr.select_region_ocr_backend", lambda engine: FakeOCRBackend())

    rows, metadata = extract_detector_crop_rows(
        image_path,
        rows=[(0, 220)],
        cols=[(0, 360)],
        exclusions=[],
        ocr_engine="auto",
    )

    assert metadata["detector_backend"] == "geometry-text-region"
    assert metadata["ocr_backend"] == "fake-region-ocr"
    assert rows
    assert rows[0].zone == "A1"
    assert rows[0].status == "review"
    assert rows[0].source_bbox is not None
