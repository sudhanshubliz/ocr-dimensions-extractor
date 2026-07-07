from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from cad_dimensions.geometry import BBox, ExclusionRegion
from cad_dimensions.models import DimensionRow, dimension_to_record, part_number_from_filename
from cad_dimensions.parser import parse_dimensions
from cad_dimensions.validation import validate_dimension


def test_part_number_from_filename() -> None:
    part_number = part_number_from_filename(Path("4022.701.44302-110-001-01.pdf"))
    assert part_number == "4022.701.4430"


def test_parse_symmetric_tolerance_with_multiplicity() -> None:
    parsed = parse_dimensions("114,3 +/- 0,25 (2x)", "B1", avg_conf=88)
    row = parsed[0].row
    assert row.nominal == Decimal("114.3")
    assert row.tolerance_value == Decimal("0.25")
    assert row.multiplicity == 2


def test_parse_unilateral_tolerance() -> None:
    parsed = parse_dimensions("620 +0,2/-0", "C5", avg_conf=90)
    row = parsed[0].row
    assert row.nominal == Decimal("620")
    assert row.lower_delta == Decimal("0")
    assert row.upper_delta == Decimal("0.2")


def test_parse_reference_dimension() -> None:
    parsed = parse_dimensions("(573)", "E6", avg_conf=90)
    assert any(row.row.tolerance_text == "Reference" and row.row.nominal == Decimal("573") for row in parsed)


def test_lower_upper_limit_calculation() -> None:
    row = DimensionRow("A2", Decimal("479"), "+/-1", Decimal("1"), Decimal("1"), Decimal("1"))
    record = dimension_to_record(row, "4022.701.4430", "drawing.pdf", index=1)
    assert record["Lower Limit"] == 478.0
    assert record["Upper Limit"] == 480.0


def test_reject_title_block_like_numbers() -> None:
    row = DimensionRow("H10", Decimal("4022"), "+/-1", Decimal("1"), Decimal("1"), Decimal("1"), source="ocr")
    validated = validate_dimension(row, "Part Number 4022.701.4430")
    assert validated.status == "rejected"
    assert "metadata" in validated.rejection_reason


def test_reject_exclusion_region_candidate() -> None:
    row = DimensionRow(
        "B2",
        Decimal("12"),
        "+/-1",
        Decimal("1"),
        Decimal("1"),
        Decimal("1"),
        source="ocr",
        source_bbox=BBox(10, 10, 50, 30),
    )
    exclusions = [ExclusionRegion("title_block", BBox(0, 0, 100, 100))]
    validated = validate_dimension(row, "12 +/-1", exclusions)
    assert validated.status == "rejected"
    assert "in_exclusion_region:title_block" in validated.rejection_reason
