from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import cv2
import numpy as np

from cad_dimensions.backends import VLMVerification
from cad_dimensions.geometry import BBox
from cad_dimensions.models import DimensionRow, ExtractionResult, dimension_to_record
from cad_dimensions.pipeline import write_result_artifacts


class FakeVerifier:
    name = "fake-vlm"
    version = "test"

    def verify(self, crop_path: Path, ocr_text: str) -> VLMVerification:
        return VLMVerification(
            text="12 +/-1",
            needs_review=False,
            confidence=0.92,
            reason="test verifier",
            payload={"nominal": "12", "tolerance": "+/-1"},
        )


def test_vlm_verifier_attaches_review_evidence_without_accepting(tmp_path: Path, monkeypatch) -> None:
    image_path = tmp_path / "page.png"
    image = np.full((120, 200, 3), 255, dtype=np.uint8)
    cv2.putText(image, "12 +/-1", (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    cv2.imwrite(str(image_path), image)

    row = DimensionRow(
        "A1",
        Decimal("12"),
        "+/-1",
        Decimal("1"),
        Decimal("1"),
        Decimal("1"),
        source="ocr",
        source_bbox=BBox(15, 35, 100, 70),
        status="review",
    )
    record = dimension_to_record(row, "4022.000.0000", "sample.pdf", index=1)
    result = ExtractionResult(Path("sample.pdf"), "4022.000.0000", "detector-crop-ocr-review", [record], 0, {"notes": "test"})

    monkeypatch.setattr("cad_dimensions.pipeline.select_vlm_verifier", lambda engine: FakeVerifier())
    write_result_artifacts(result, tmp_path / "run", image_path, vlm_verifier="qwen")

    assert result.rows[0]["status"] == "review"
    assert result.rows[0]["vlm_verification"]["text"] == "12 +/-1"
    assert result.rows[0]["vlm_verification"]["payload"]["nominal"] == "12"
