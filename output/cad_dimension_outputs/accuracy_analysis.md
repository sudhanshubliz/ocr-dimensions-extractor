# CAD Dimension Batch Accuracy Analysis

## Test set

The batch run covered 12 PDFs:

- 4022.701.44302-110-001-01.pdf
- 4022.704.85852-110-001-01.pdf
- 4022.708.24341-110-001-01.pdf
- 4022.708.24915-110-001-01.pdf
- 4022.708.80131-110-001-01.pdf
- 4022.708.80161-110-001-02.pdf
- 4022.708.86631-110-001-02.pdf
- 4022.708.87491-110-001-01.pdf
- 4022.712.00591-110-001-01.pdf
- 4022.713.00542-110-001-01.pdf
- 4022.713.01001-110-001-01.pdf
- 4022.713.01322-110-001-01.pdf

## Result

All PDFs have zero extractable PDF text-layer characters. The drawing text is
plotted as vector paths, so normal PDF text extraction is not enough.

Only `4022.701.44302-110-001-01.pdf` is currently template-confirmed. The other
PDFs use generic OCR candidates and must be manually reviewed against the source
PDF/CAD drawing before being used for inspection or manufacturing.

The batch workbook is:

```text
cad_dimension_outputs/cad_dimension_batch_analysis.xlsx
```

## Accuracy conclusion

The current generic OCR fallback is useful for candidate discovery only. It is
not inspection-grade. It still catches false positives from title blocks, notes,
and drawing labels, and it can misread CAD decimal commas or missing decimal
points.

For higher accuracy, the next version should add:

1. CAD/DXF/native extraction whenever available.
2. Geometry-based text-region detection before OCR.
3. OCR only on cropped dimension text regions, not the whole drawing.
4. A dimension grammar and validation layer that rejects title-block text,
   part numbers, generic notes, and impossible tolerance ratios.
5. Human review workflow for candidates below the confidence threshold.

## Recommended model direction

Use a specialized OCR/detector first, then optionally use a VLM/LLM for review:

- PaddleOCR / PP-OCRv5 for text detection and recognition.
- A custom YOLO/RT-DETR detector trained to find dimension annotations, arrows,
  and title-block exclusion regions.
- Qwen2.5-VL, Donut, or OpenAI vision models as secondary validation/review
  tools, not as the only source of numeric truth.

General VLMs are useful for reasoning over a cropped region, but they can still
hallucinate or normalize numbers incorrectly. Final numeric extraction should be
validated by deterministic geometry and engineering tolerance rules.
