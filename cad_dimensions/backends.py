from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from .geometry import BBox


@dataclass(frozen=True)
class Detection:
    bbox: BBox
    label: str
    confidence: float
    page_number: int = 1


@dataclass(frozen=True)
class OCRCandidate:
    text: str
    bbox: BBox
    confidence: int
    page_number: int = 1


@dataclass(frozen=True)
class VLMVerification:
    text: str
    needs_review: bool
    confidence: float
    reason: str = ""


class DetectorBackend(ABC):
    name = "detector"
    version = "unconfigured"

    @abstractmethod
    def detect(self, image_path: Path) -> list[Detection]:
        """Return candidate dimension/exclusion regions for a rendered page."""


class OCRBackend(ABC):
    name = "ocr"
    version = "unconfigured"

    @abstractmethod
    def recognize(self, image_path: Path, regions: list[Detection] | None = None) -> list[OCRCandidate]:
        """Return OCR text candidates, optionally constrained to detector regions."""


class VLMVerifierBackend(ABC):
    name = "vlm"
    version = "disabled"

    @abstractmethod
    def verify(self, crop_path: Path, ocr_text: str) -> VLMVerification:
        """Verify a review crop. This must not bypass deterministic validators."""


class DisabledVLMVerifier(VLMVerifierBackend):
    name = "disabled-vlm"
    version = "0"

    def verify(self, crop_path: Path, ocr_text: str) -> VLMVerification:
        return VLMVerification(text=ocr_text, needs_review=True, confidence=0.0, reason="VLM verifier is disabled.")
