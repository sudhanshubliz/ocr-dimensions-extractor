from __future__ import annotations

from pathlib import Path
import json

import pandas as pd

from .models import OUTPUT_COLUMNS, SUMMARY_COLUMNS, public_record


def _excel_safe_rows(rows: list[dict]) -> list[dict]:
    return [public_record(row) for row in rows if row.get("status") != "rejected"]


def write_dimensions_excel(rows: list[dict], output_path: Path) -> None:
    df = pd.DataFrame(_excel_safe_rows(rows), columns=OUTPUT_COLUMNS)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Dimensions", index=False)
        ws = writer.book["Dimensions"]
        ws.freeze_panes = "A2"
        for col, width in {"A": 18, "B": 9, "C": 18, "D": 14, "E": 16, "F": 12, "G": 13, "H": 13, "I": 13, "J": 42}.items():
            ws.column_dimensions[col].width = width


def write_batch_excel(all_rows: list[dict], summary_rows: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        pd.DataFrame(summary_rows, columns=SUMMARY_COLUMNS).to_excel(writer, sheet_name="Summary", index=False)
        pd.DataFrame(_excel_safe_rows(all_rows), columns=OUTPUT_COLUMNS).to_excel(writer, sheet_name="All Dimensions", index=False)
        for ws in writer.book.worksheets:
            ws.freeze_panes = "A2"
            for col in range(1, ws.max_column + 1):
                ws.column_dimensions[ws.cell(1, col).column_letter].width = min(46, max(12, len(str(ws.cell(1, col).value)) + 4))


def write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
