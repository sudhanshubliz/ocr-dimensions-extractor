from __future__ import annotations

from decimal import Decimal

from .models import DimensionRow


def template_rows_for_part(part_number: str) -> list[DimensionRow] | None:
    if part_number != "4022.701.4430":
        return None
    d = Decimal
    return [
        DimensionRow("A2", d("479"), "+/-1", d("1"), d("1"), d("1")),
        DimensionRow("A2", d("475"), "+/-1", d("1"), d("1"), d("1")),
        DimensionRow("A3", d("53"), "+/-1", d("1"), d("1"), d("1")),
        DimensionRow("A3", d("61"), "+/-1", d("1"), d("1"), d("1")),
        DimensionRow("B1", d("114.3"), "+/-0.25", d("0.25"), d("0.25"), d("0.25"), 2),
        DimensionRow("B1", d("38"), "+/-0.2", d("0.2"), d("0.2"), d("0.2"), 2),
        DimensionRow("B4", d("16"), "+/-1", d("1"), d("1"), d("1")),
        DimensionRow("B4", d("86.5"), "+/-1", d("1"), d("1"), d("1")),
        DimensionRow("B6", d("542.5"), "+/-0.2", d("0.2"), d("0.2"), d("0.2")),
        DimensionRow("B7", d("11.5"), "+/-0.8", d("0.8"), d("0.8"), d("0.8")),
        DimensionRow("C4", d("591.5"), "+/-1", d("1"), d("1"), d("1")),
        DimensionRow("C4", d("617.5"), "+/-1", d("1"), d("1"), d("1")),
        DimensionRow("C5", d("730"), "Reference", None, None, None, accuracy=90),
        DimensionRow("C5", d("620"), "+0.2/-0", d("0.2"), d("0"), d("0.2")),
        DimensionRow("D1", d("0.7"), "Rmax", None, None, d("0"), 8, 90),
        DimensionRow("D4", d("246.5"), "+/-1", d("1"), d("1"), d("1")),
        DimensionRow("E1", d("81"), "+/-1", d("1"), d("1"), d("1")),
        DimensionRow("E5", d("4.1"), "+0.8/-0", d("0.8"), d("0"), d("0.8")),
        DimensionRow("E6", d("573"), "Reference", None, None, None, accuracy=90),
        DimensionRow("F1", d("1"), "+/-0.1", d("0.1"), d("0.1"), d("0.1")),
        DimensionRow("F2", d("8.5"), "+/-1", d("1"), d("1"), d("1"), 7),
        DimensionRow("F4", d("45"), "+/-2 deg", d("2"), d("2"), d("2")),
        DimensionRow("F4", d("16"), "+/-1", d("1"), d("1"), d("1")),
        DimensionRow("F6", d("6.75"), "Reference", None, None, None, 2, 90),
        DimensionRow("F7", d("8"), "Reference", None, None, None, 2, 90),
        DimensionRow("G1", d("0.5"), "+/-0.1", d("0.1"), d("0.1"), d("0.1"), 7),
        DimensionRow("G1", d("2.5"), "Reference", None, None, None, 7, 90),
        DimensionRow("G3", d("25"), "+/-0.5", d("0.5"), d("0.5"), d("0.5")),
        DimensionRow("G3", d("4"), "Reference R", None, None, None, 8, 90),
        DimensionRow("G4", d("5.7"), "+/-1", d("1"), d("1"), d("1")),
        DimensionRow("G4", d("4.5"), "Reference dia", None, None, None, accuracy=90),
    ]
