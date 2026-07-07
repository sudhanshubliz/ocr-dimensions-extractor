# OCR Dimensions Extractor

This repository contains experiments and tooling for extracting CAD drawing
dimensions into Excel.

## CAD grid-first hybrid extraction

The current recommended workflow for ASML-style CAD layout PDFs is exposed by
`cad_grid_hybrid_extractor.py` and implemented in the modular `cad_dimensions/`
package.

Production MLOps planning is documented here:

```text
docs/mlops_cad_dimension_pipeline.md
mlops/pipeline.yaml
```

### Why this approach

Some CAD PDFs, including `4022.701.44302-110-001-01.pdf`, do not contain normal
selectable text. The drawing text is plotted as vector paths. In this case:

- PDF text extraction returns no usable characters.
- Full-page OCR can read some dimensions, but it often creates unsafe numeric
  errors such as `5425` instead of `542.5`, `47.5` instead of `475`, or
  `620 +/-2` instead of `620 +0.2/-0`.
- Zone detection based on OCR labels is fragile when grid ticks or labels are
  missed.

The safer technique is grid-first extraction:

1. Render the PDF page at high resolution.
2. Detect the CAD sheet border/grid using image geometry.
3. Assign zones from the drawing grid, such as `A2`, `B6`, `G4`.
4. Parse dimension values using strict engineering rules.
5. Export the agreed Excel columns.

For production use, OCR should be applied only to focused dimension regions
rather than the full drawing page. This keeps OCR from mixing title-block notes,
view labels, grid labels, and drawing dimensions into false dimension rows.

### Modules

The extractor is split into small modules:

```text
cad_dimensions/models.py      Shared row schema and dataclasses
cad_dimensions/rendering.py   PDF-to-image rendering
cad_dimensions/grid.py        CAD border/grid detection and zone mapping
cad_dimensions/parser.py      Dimension/tolerance grammar
cad_dimensions/ocr.py         Review-level OCR candidate extraction
cad_dimensions/validation.py  Deterministic row validators
cad_dimensions/exclusions.py  Title block, notes, border, and grid exclusions
cad_dimensions/crops.py       Crop snapshots for OCR candidate rows
cad_dimensions/backends.py    Detector/OCR/VLM backend interfaces
cad_dimensions/templates.py   Known template-confirmed dimensions
cad_dimensions/export.py      Excel writers
cad_dimensions/pipeline.py    Single-file and batch orchestration
cad_dimensions/cli.py         Command-line interface
cad_dimensions/api.py         Local FastAPI app
cad_dimensions/storage.py     Local SQLite persistence
```

### Output columns

The Excel output uses this schema:

```text
Part Number
Zone
Nominal Dimension
Tolerance
Tolerance Value
Accuracy %
Multiplicity
Lower Limit
Upper Limit
File Name
```

### Example

Run:

```bash
python cad_grid_hybrid_extractor.py \
  4022.701.44302-110-001-01.pdf \
  4022.701.4430_grid_hybrid_extract.xlsx
```

The included sample output is:

```text
4022.701.4430_grid_hybrid_extract.xlsx
```

Batch run:

```bash
python cad_grid_hybrid_extractor.py \
  -o runs \
  4022.701.44302-110-001-01.pdf \
  4022.704.85852-110-001-01.pdf
```

This writes one timestamped run folder:

```text
runs/<timestamp>/
  summary.xlsx
  dimensions.json
  audit_report.json
  crops/
  <pdf-stem>/
    dimensions.json
    audit_report.json
    crops/
    <part-number>_dimensions.xlsx
```

Use `--flat-output` when you want batch artifacts written directly inside the
chosen output folder.

### Structured output

Excel remains limited to the user-facing columns:

```text
Part Number | Zone | Nominal Dimension | Tolerance | Tolerance Value |
Accuracy % | Multiplicity | Lower Limit | Upper Limit | File Name
```

The JSON/audit output also includes production review metadata:

```text
dimension_id
source_bbox
page_number
status: accepted | review | rejected
rejection_reason
source: template | ocr | human | vlm
crop_path
```

Template-confirmed rows can be `accepted`. Unknown generic OCR rows are kept as
`review` unless deterministic validators reject them.

### Local API

Start the local secure API with:

```bash
uvicorn cad_dimensions.api:app --reload
```

Available endpoints:

```text
POST  /documents
POST  /documents/{id}/extract
GET   /jobs/{id}
GET   /documents/{id}/dimensions
PATCH /dimensions/{id}
POST  /documents/{id}/export/xlsx
```

The first implementation uses local filesystem storage under `.cad_dimension_app/`
and SQLite. There are no cloud calls by default.

### Tests

Run:

```bash
pytest
```

Coverage includes tolerance parsing, unilateral tolerances, reference dimensions,
lower/upper limit calculation, title-block rejection, exclusion-region rejection,
golden template rows for `4022.701.4430`, artifact generation, and local review
storage.

### Model upgrade path

The first production source of truth is deterministic geometry plus validation.
Model components are intentionally replaceable:

```text
DetectorBackend -> YOLO / RT-DETR later
OCRBackend      -> Tesseract now, PaddleOCR / PP-OCRv5 next
VLMVerifier     -> disabled by default, optional review-only verifier later
```

VLM output should never bypass deterministic CAD/tolerance validation.

### Notes on precision

Use CAD/PDF-rendered dimension text as the source of values. Do not measure
distances from screenshots or rendered pixels to infer nominal dimensions. Pixel
geometry is useful for locating zones and text regions, but the engineering value
must come from the printed dimension annotation or native CAD data.

### Current limitation

Known drawing templates use template-confirmed values. Unknown drawings use
generic OCR candidates with review-level confidence. The generic OCR path is not
yet inspection-grade by itself; it is intended to identify candidate dimensions
that should be checked against the original PDF/CAD drawing.

The next production step is to train or configure a focused detector for
dimension text regions, then run OCR/vision only on those regions and validate
the result with the engineering dimension grammar.
