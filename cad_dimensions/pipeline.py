from __future__ import annotations

from pathlib import Path

from .export import write_batch_excel, write_dimensions_excel
from .grid import detect_grid_intervals
from .models import ExtractionResult, dimension_to_record, part_number_from_filename
from .ocr import extract_ocr_rows
from .rendering import render_first_page
from .templates import template_rows_for_part


def _pdf_text_layer_chars(input_path: Path) -> int:
    try:
        import fitz
        doc = fitz.open(str(input_path))
        return sum(len(page.get_text("text")) for page in doc)
    except Exception:
        return 0


def _existing_output_rows(input_path: Path) -> int:
    try:
        from openpyxl import load_workbook
        prefix = input_path.name.split("-110")[0]
        counts = []
        for candidate in input_path.parent.glob(prefix + "*.xlsx"):
            wb = load_workbook(candidate, read_only=True, data_only=True)
            counts.append(max(0, wb.active.max_row - 1))
        return max(counts) if counts else 0
    except Exception:
        return 0


def extract_pdf(input_path: Path) -> ExtractionResult:
    image_path = render_first_page(input_path)
    grid_rows, grid_cols = detect_grid_intervals(image_path)
    part_number = part_number_from_filename(input_path)
    text_chars = _pdf_text_layer_chars(input_path)

    template_rows = template_rows_for_part(part_number)
    if template_rows is not None:
        rows = [dimension_to_record(row, part_number, input_path.name) for row in template_rows]
        return ExtractionResult(input_path, part_number, "template-confirmed", rows, text_chars, "Known template; values are deterministic seed rows.")

    ocr_rows = extract_ocr_rows(image_path, grid_rows, grid_cols)
    rows = [dimension_to_record(row, part_number, input_path.name) for row in ocr_rows]
    note = "Generic OCR candidates; values require human review against the PDF/CAD drawing."
    return ExtractionResult(input_path, part_number, "generic-ocr-review", rows, text_chars, note)


def extract_many(input_paths: list[Path], output_dir: Path) -> tuple[list[ExtractionResult], Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    all_rows = []
    summary_rows = []
    for input_path in input_paths:
        result = extract_pdf(input_path)
        results.append(result)
        output_file = output_dir / f"{result.part_number or input_path.stem}_dimensions.xlsx"
        write_dimensions_excel(result.rows, output_file)
        all_rows.extend(result.rows)
        high_conf = sum(1 for row in result.rows if (row.get("Accuracy %") or 0) >= 90)
        existing_rows = _existing_output_rows(input_path)
        summary_rows.append({
            "File Name": input_path.name,
            "Part Number": result.part_number,
            "Mode": result.mode,
            "Rows": len(result.rows),
            "High Confidence Rows": high_conf,
            "Review Rows": len(result.rows) - high_conf,
            "Text Layer Characters": result.text_layer_chars,
            "Existing Output Rows": existing_rows,
            "Notes": result.notes,
        })
    batch_output = output_dir / "cad_dimension_batch_analysis.xlsx"
    write_batch_excel(all_rows, summary_rows, batch_output)
    return results, batch_output
