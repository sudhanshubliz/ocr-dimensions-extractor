# OCR Dimensions Extractor

This repository contains experiments and tooling for extracting CAD drawing
dimensions into Excel.

## CAD grid-first hybrid extraction

The current recommended workflow for ASML-style CAD layout PDFs is implemented in
`cad_grid_hybrid_extractor.py`.

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

### Notes on precision

Use CAD/PDF-rendered dimension text as the source of values. Do not measure
distances from screenshots or rendered pixels to infer nominal dimensions. Pixel
geometry is useful for locating zones and text regions, but the engineering value
must come from the printed dimension annotation or native CAD data.

### Current limitation

`cad_grid_hybrid_extractor.py` currently includes conservative deterministic
dimension recovery for the included sample drawing family. The next production
step is to replace those deterministic rows with focused region OCR plus
cross-checks against a validated dimension grammar.
