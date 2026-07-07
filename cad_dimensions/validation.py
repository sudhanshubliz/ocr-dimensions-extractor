from __future__ import annotations

import re
from dataclasses import replace
from decimal import Decimal

from .geometry import ExclusionRegion, any_intersection
from .models import DimensionRow

PART_OR_DATE_RE = re.compile(r"(4022|20\d{2}[-./]\d{1,2}|AISI|STAINLESS|SHEET|MATERIAL|SCALE)", re.IGNORECASE)
ZONE_RE = re.compile(r"^[A-H](?:[1-9]|10)$")


def validate_dimension(row: DimensionRow, raw_text: str = "", exclusions: list[ExclusionRegion] | None = None) -> DimensionRow:
    reasons: list[str] = []
    exclusions = exclusions or []

    if not row.zone:
        reasons.append("missing_zone")
    elif not ZONE_RE.match(row.zone):
        reasons.append("invalid_zone")

    exclusion_name = any_intersection(row.source_bbox, exclusions)
    if exclusion_name:
        reasons.append(f"in_exclusion_region:{exclusion_name}")

    if raw_text and PART_OR_DATE_RE.search(raw_text):
        reasons.append("looks_like_title_block_or_metadata")

    if row.nominal <= 0:
        reasons.append("non_positive_nominal")

    if row.tolerance_value is not None:
        if row.tolerance_value < 0:
            reasons.append("negative_tolerance")
        if row.tolerance_value > max(abs(row.nominal) * Decimal("0.6"), Decimal("10")):
            reasons.append("implausible_tolerance_ratio")

    if row.lower_delta is not None and row.upper_delta is not None:
        lower = row.nominal - row.lower_delta
        upper = row.nominal + row.upper_delta
        if lower > upper:
            reasons.append("invalid_limits")

    if reasons:
        return replace(row, status="rejected", rejection_reason=";".join(reasons), accuracy=min(row.accuracy, 40))

    if row.source == "template":
        return replace(row, status="accepted", rejection_reason="")

    return replace(row, status="review", rejection_reason="")
