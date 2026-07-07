from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from .geometry import BBox


OUTPUT_COLUMNS = [
    "Part Number",
    "Zone",
    "Nominal Dimension",
    "Tolerance",
    "Tolerance Value",
    "Accuracy %",
    "Multiplicity",
    "Lower Limit",
    "Upper Limit",
    "File Name",
]

SUMMARY_COLUMNS = [
    "File Name",
    "Part Number",
    "Mode",
    "Rows",
    "Accepted Rows",
    "Review Rows",
    "Rejected Rows",
    "High Confidence Rows",
    "Text Layer Characters",
    "Existing Output Rows",
    "Notes",
]

VALID_STATUSES = {"accepted", "review", "rejected"}


@dataclass(frozen=True)
class DimensionRow:
    zone: str
    nominal: Decimal
    tolerance_text: str
    tolerance_value: Decimal | None
    lower_delta: Decimal | None
    upper_delta: Decimal | None
    multiplicity: int | None = None
    accuracy: int = 95
    source: str = "template"
    source_bbox: BBox | None = None
    page_number: int = 1
    status: str | None = None
    rejection_reason: str = ""


@dataclass(frozen=True)
class ExtractionResult:
    input_path: Path
    part_number: str
    mode: str
    rows: list[dict]
    text_layer_chars: int
    notes: str | dict = ""
    run_dir: Path | None = None


def decimal_to_float(value: Decimal | None) -> float | None:
    return None if value is None else float(value)


def part_number_from_filename(path: Path) -> str:
    digits = re.sub(r"\D", "", path.name)
    match = re.search(r"(4022\d{7})", digits)
    if match:
        raw = match.group(1)
        return f"{raw[:4]}.{raw[4:7]}.{raw[7:11]}"
    return ""


def dimension_id_for(file_name: str, row: DimensionRow, index: int = 0) -> str:
    clean_file = re.sub(r"[^A-Za-z0-9]+", "-", Path(file_name).stem).strip("-")
    clean_zone = row.zone or "NOZONE"
    nominal = str(row.nominal).replace(".", "p").replace("-", "m")
    return f"{clean_file}-{clean_zone}-{nominal}-{index:04d}"


def dimension_to_record(row: DimensionRow, part_number: str, file_name: str, index: int = 0) -> dict:
    lower = row.nominal - row.lower_delta if row.lower_delta is not None else None
    upper = row.nominal + row.upper_delta if row.upper_delta is not None else None
    status = row.status or ("accepted" if row.source == "template" else "review")
    if status not in VALID_STATUSES:
        status = "review"
    return {
        "dimension_id": dimension_id_for(file_name, row, index),
        "Part Number": part_number,
        "Zone": row.zone,
        "Nominal Dimension": decimal_to_float(row.nominal),
        "Tolerance": row.tolerance_text,
        "Tolerance Value": decimal_to_float(row.tolerance_value),
        "Accuracy %": row.accuracy,
        "Multiplicity": row.multiplicity or "",
        "Lower Limit": decimal_to_float(lower),
        "Upper Limit": decimal_to_float(upper),
        "File Name": file_name,
        "source_bbox": row.source_bbox.to_dict() if row.source_bbox else None,
        "page_number": row.page_number,
        "status": status,
        "rejection_reason": row.rejection_reason,
        "source": row.source,
    }


def public_record(record: dict) -> dict:
    return {column: record.get(column) for column in OUTPUT_COLUMNS}
