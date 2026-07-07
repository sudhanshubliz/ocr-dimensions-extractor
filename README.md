# OCR Dimensions Extractor

This repository contains experiments and tooling for extracting CAD drawing
dimensions into Excel.

## CAD grid-first hybrid extraction

The current recommended workflow for ASML-style CAD layout PDFs is exposed by
`cad_grid_hybrid_extractor.py` and implemented in the modular `cad_dimensions/`
package.

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
cad_dimensions/templates.py   Known template-confirmed dimensions
cad_dimensions/export.py      Excel writers
cad_dimensions/pipeline.py    Single-file and batch orchestration
cad_dimensions/cli.py         Command-line interface
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
  -o cad_dimension_outputs \
  4022.701.44302-110-001-01.pdf \
  4022.704.85852-110-001-01.pdf
```

This writes one workbook per PDF plus:

```text
cad_dimension_outputs/cad_dimension_batch_analysis.xlsx
```

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
