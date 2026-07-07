from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path


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
    "High Confidence Rows",
    "Review Rows",
    "Text Layer Characters",
    "Existing Output Rows",
    "Notes",
]


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


@dataclass(frozen=True)
class ExtractionResult:
    input_path: Path
    part_number: str
    mode: str
    rows: list[dict]
    text_layer_chars: int
    notes: str = ""


def decimal_to_float(value: Decimal | None) -> float | None:
    return None if value is None else float(value)


def part_number_from_filename(path: Path) -> str:
    digits = re.sub(r"\D", "", path.name)
    match = re.search(r"(4022\d{7})", digits)
    if match:
        raw = match.group(1)
        return f"{raw[:4]}.{raw[4:7]}.{raw[7:11]}"
    return ""


def dimension_to_record(row: DimensionRow, part_number: str, file_name: str) -> dict:
    lower = row.nominal - row.lower_delta if row.lower_delta is not None else None
    upper = row.nominal + row.upper_delta if row.upper_delta is not None else None
    return {
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
    }
