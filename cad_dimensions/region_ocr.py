from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import pytesseract

from .backends import Detection, OCRBackend, OCRCandidate
from .geometry import BBox


@dataclass(frozen=True)
class OCRBackendStatus:
    name: str
    version: str
    available: bool
    reason: str = ""


def _crop(image: np.ndarray, bbox: BBox, pad: int = 10) -> np.ndarray:
    height, width = image.shape[:2]
    box = bbox.expand(pad, width, height)
    return image[box.y0 : box.y1, box.x0 : box.x1]


def _rotate(image: np.ndarray, angle: int) -> np.ndarray:
    if angle == 90:
        return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    if angle == 270:
        return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return image


def _best_tesseract_text(image: np.ndarray) -> tuple[str, int]:
    best_text = ""
    best_conf = -1
    for angle in (0, 90, 270):
        rotated = _rotate(image, angle)
        data = pytesseract.image_to_data(rotated, output_type=pytesseract.Output.DICT, config="--oem 3 --psm 6")
        tokens: list[str] = []
        confs: list[int] = []
        for idx, raw_text in enumerate(data.get("text", [])):
            text = str(raw_text).strip()
            if not text:
                continue
            raw_conf = str(data["conf"][idx])
            conf = int(float(raw_conf)) if raw_conf.replace(".", "", 1).lstrip("-").isdigit() else -1
            if conf < 15:
                continue
            tokens.append(text)
            confs.append(conf)
        if not tokens:
            continue
        avg_conf = int(sum(confs) / len(confs))
        if avg_conf > best_conf:
            best_text = " ".join(tokens)
            best_conf = avg_conf
    return best_text, max(0, best_conf)


class TesseractRegionOCRBackend(OCRBackend):
    name = "tesseract-region"
    version = "0.1"

    def recognize(self, image_path: Path, regions: list[Detection] | None = None) -> list[OCRCandidate]:
        image = cv2.imread(str(image_path))
        if image is None:
            return []
        if not regions:
            return []
        candidates: list[OCRCandidate] = []
        for region in regions:
            crop = _crop(image, region.bbox)
            if crop.size == 0:
                continue
            text, confidence = _best_tesseract_text(crop)
            if text:
                candidates.append(OCRCandidate(text, region.bbox, confidence, region.page_number))
        return candidates


class PaddleRegionOCRBackend(OCRBackend):
    name = "paddleocr-region"
    version = "pp-ocrv5-compatible"

    def __init__(self) -> None:
        self._ocr = self._init_paddleocr()

    @staticmethod
    def status() -> OCRBackendStatus:
        try:
            import paddleocr  # noqa: F401

            return OCRBackendStatus(PaddleRegionOCRBackend.name, PaddleRegionOCRBackend.version, True)
        except Exception as exc:
            return OCRBackendStatus(PaddleRegionOCRBackend.name, PaddleRegionOCRBackend.version, False, str(exc))

    def recognize(self, image_path: Path, regions: list[Detection] | None = None) -> list[OCRCandidate]:
        image = cv2.imread(str(image_path))
        if image is None or not regions:
            return []
        candidates: list[OCRCandidate] = []
        for region in regions:
            crop = _crop(image, region.bbox)
            if crop.size == 0:
                continue
            text, confidence = self._best_paddle_text(crop)
            if text:
                candidates.append(OCRCandidate(text, region.bbox, confidence, region.page_number))
        return candidates

    def _init_paddleocr(self):
        from paddleocr import PaddleOCR

        init_attempts = [
            {
                "lang": "en",
                "ocr_version": "PP-OCRv5",
                "use_doc_orientation_classify": False,
                "use_doc_unwarping": False,
                "use_textline_orientation": True,
            },
            {
                "lang": "en",
                "ocr_version": "PP-OCRv5",
                "use_angle_cls": True,
            },
            {
                "lang": "en",
                "use_angle_cls": True,
            },
            {
                "lang": "en",
            },
        ]
        last_error: Exception | None = None
        for kwargs in init_attempts:
            try:
                return PaddleOCR(**kwargs)
            except Exception as exc:
                last_error = exc
        if last_error:
            raise last_error
        return PaddleOCR(lang="en")

    def _best_paddle_text(self, image: np.ndarray) -> tuple[str, int]:
        best_text = ""
        best_conf = 0
        for angle in (0, 90, 270):
            rotated = _rotate(image, angle)
            result = self._predict(rotated)
            text, confidence = self._flatten_result(result)
            if confidence > best_conf:
                best_text = text
                best_conf = confidence
        return best_text, best_conf

    def _predict(self, image: np.ndarray):
        if hasattr(self._ocr, "predict"):
            return self._ocr.predict(image)
        return self._ocr.ocr(image, cls=True)

    def _flatten_result(self, result) -> tuple[str, int]:
        texts: list[str] = []
        confs: list[float] = []
        self._collect_text_confidence(result, texts, confs)
        if not texts:
            return "", 0
        confidence = int(round((sum(confs) / len(confs)) * 100)) if confs else 70
        return " ".join(texts), max(0, min(99, confidence))

    def _collect_text_confidence(self, value, texts: list[str], confs: list[float]) -> None:
        if value is None:
            return
        if isinstance(value, dict):
            rec_texts = value.get("rec_texts")
            rec_scores = value.get("rec_scores")
            if isinstance(rec_texts, list):
                texts.extend(str(item).strip() for item in rec_texts if str(item).strip())
                if isinstance(rec_scores, list):
                    confs.extend(float(score) for score in rec_scores if isinstance(score, (int, float)))
                return
            for child in value.values():
                self._collect_text_confidence(child, texts, confs)
            return
        if isinstance(value, tuple) and len(value) >= 2 and isinstance(value[0], str):
            text = value[0].strip()
            if text:
                texts.append(text)
                if isinstance(value[1], (int, float)):
                    confs.append(float(value[1]))
            return
        if isinstance(value, list):
            if len(value) >= 2 and isinstance(value[1], tuple) and len(value[1]) >= 2:
                text = str(value[1][0]).strip()
                if text:
                    texts.append(text)
                    if isinstance(value[1][1], (int, float)):
                        confs.append(float(value[1][1]))
                return
            for child in value:
                self._collect_text_confidence(child, texts, confs)


def select_region_ocr_backend(engine: str = "auto") -> OCRBackend:
    normalized = engine.lower()
    if normalized == "paddle":
        return PaddleRegionOCRBackend()
    if normalized == "tesseract":
        return TesseractRegionOCRBackend()
    if normalized == "auto" and PaddleRegionOCRBackend.status().available:
        try:
            return PaddleRegionOCRBackend()
        except Exception:
            return TesseractRegionOCRBackend()
    return TesseractRegionOCRBackend()
