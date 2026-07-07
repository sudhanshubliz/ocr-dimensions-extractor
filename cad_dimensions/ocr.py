from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytesseract

from .grid import zone_for_point
from .models import DimensionRow
from .parser import parse_dimensions


def _preprocess(gray: np.ndarray) -> list[np.ndarray]:
    variants = [gray]
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    variants.append(clahe.apply(gray))
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    _, otsu = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    variants.append(otsu)
    return variants


def _token_lines(gray: np.ndarray) -> list[dict]:
    data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT, config="--oem 3 --psm 6")
    groups: dict[tuple[int, int, int], list[dict]] = {}
    for idx, raw_text in enumerate(data.get("text", [])):
        text = str(raw_text).strip()
        if not text:
            continue
        conf = int(float(data["conf"][idx])) if str(data["conf"][idx]).replace(".", "", 1).lstrip("-").isdigit() else -1
        if conf < 20:
            continue
        key = (int(data["block_num"][idx]), int(data["par_num"][idx]), int(data["line_num"][idx]))
        groups.setdefault(key, []).append({
            "text": text,
            "conf": conf,
            "left": int(data["left"][idx]),
            "top": int(data["top"][idx]),
            "width": int(data["width"][idx]),
            "height": int(data["height"][idx]),
        })

    lines = []
    for tokens in groups.values():
        tokens.sort(key=lambda item: item["left"])
        text = " ".join(item["text"] for item in tokens)
        left = min(item["left"] for item in tokens)
        top = min(item["top"] for item in tokens)
        right = max(item["left"] + item["width"] for item in tokens)
        bottom = max(item["top"] + item["height"] for item in tokens)
        avg_conf = int(sum(item["conf"] for item in tokens) / len(tokens))
        lines.append({
            "text": text,
            "cx": (left + right) / 2,
            "cy": (top + bottom) / 2,
            "avg_conf": avg_conf,
        })
    return lines


def extract_ocr_rows(image_path: Path, rows: list[tuple[int, int]], cols: list[tuple[int, int]]) -> list[DimensionRow]:
    image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        return []

    found: dict[tuple[str, float, str], DimensionRow] = {}
    for variant in _preprocess(image):
        for line in _token_lines(variant):
            zone = zone_for_point(line["cx"], line["cy"], rows, cols) or ""
            if not zone:
                continue
            for parsed in parse_dimensions(line["text"], zone, line["avg_conf"]):
                row = parsed.row
                key = (row.zone, float(row.nominal), row.tolerance_text)
                previous = found.get(key)
                if previous is None or row.accuracy > previous.accuracy:
                    found[key] = row
    return sorted(found.values(), key=lambda item: (item.zone, float(item.nominal), item.tolerance_text))
