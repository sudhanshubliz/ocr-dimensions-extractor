# ocr-dimensions-extractor

# OCR Dimensions Extractor (AWS Textract + Spatial Clustering)

A production-grade OCR dimension extraction system designed for
engineering drawings (e.g., ASML, Siemens, mechanical manufacturing).

This system uses:
- AWS Textract (synchronous AnalyzeDocument API — no S3 required)
- NumPy + SciPy for spatial clustering
- OpenCV overlay for visual debugging
- Auto zone mapping (A–H rows, 1–10 columns)
- Clean modular architecture
- Excel export via pandas/openpyxl

The system is optimized to:
- Accurately detect dimensions like "475 ± 1", "542.5 ± 0.2"
- Reject false positives like "2023 ± 5" or "44302 ± 110"
- Handle European decimal commas → converted to dot
- Avoid title block / notes region noise
- Pair nominal and tolerance values via geometric proximity
- Support part-number extraction

---

## Folder Structure

ocr-dimensions-extractor/
│
├── README.md
├── requirements.txt
│
├── ocr_dimensions/
│ ├── init.py
│ ├── engine.py
│ ├── geometry.py
│ ├── parsing.py
│ ├── zones.py
│ ├── filters.py
│ ├── part_number.py
│ ├── overlay.py
│ ├── textract_wrapper.py
│ └── utils.py
│
└── cli/
├── init.py
└── textract_runner.py


---

## Install Dependencies
pip install -r requirements.txt


---

## Run Extraction
With debug overlay:

python cli/textract_runner.py input.pdf output.xlsx --debug

Output file will include:

- Part Number
- Zone
- Nominal Dimension
- Tolerance
- Tolerance Value
- Accuracy %
- Multiplicity
- Lower Limit
- Upper Limit
- File Name

---

## Debug Overlay

When `--debug` is passed, the system generates:


This includes:
- Textract word boxes
- Nominal tokens (blue)
- Tolerance tokens (green)
- ± symbols (yellow)
- Dimension groups (red)
- Rejected candidates (gray)
- Zone grid overlay (A–H, 1–10)

---

## Requirements

See `requirements.txt`

---

## License
No Licence





