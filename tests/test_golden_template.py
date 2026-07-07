from __future__ import annotations

import json
from pathlib import Path

from cad_dimensions.models import dimension_to_record
from cad_dimensions.templates import template_rows_for_part


def test_4022_701_4430_template_matches_golden_rows() -> None:
    expected = json.loads(Path("tests/golden/4022.701.4430_expected.json").read_text(encoding="utf-8"))
    rows = [
        dimension_to_record(row, expected["part_number"], "4022.701.44302-110-001-01.pdf", index=i)
        for i, row in enumerate(template_rows_for_part(expected["part_number"]) or [], start=1)
    ]

    assert len(rows) == expected["accepted_count"]
    assert {row["status"] for row in rows} == {"accepted"}
    for actual, expected_row in zip(rows, expected["first_rows"]):
        for key, value in expected_row.items():
            assert actual[key] == value
