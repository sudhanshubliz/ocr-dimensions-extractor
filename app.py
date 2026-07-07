from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

from cad_dimensions.pipeline import extract_pdf


OUTPUT_COLUMNS = [
    "Part Number",
    "Zone",
    "Nominal Dimension",
    "Tolerance",
    "Tolerance Value",
    "Accuracy %",
    "Multiplicity",
    "Lower Limit",
    "Upper Limit",
    "File Name",
]

HOME_IMAGE_PATH = Path("assets/cad_dimension_extractor_home.png")


st.set_page_config(
    page_title="CAD Dimension Extractor",
    page_icon="CAD",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _status_counts(rows: list[dict]) -> dict[str, int]:
    return {
        "accepted": sum(1 for row in rows if row.get("status") == "accepted"),
        "review": sum(1 for row in rows if row.get("status") == "review"),
        "rejected": sum(1 for row in rows if row.get("status") == "rejected"),
    }


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _artifact_paths(run_dir: Path, pdf_path: Path, part_number: str) -> dict[str, Path]:
    doc_dir = run_dir / pdf_path.stem
    return {
        "doc_dir": doc_dir,
        "xlsx": doc_dir / f"{part_number or pdf_path.stem}_dimensions.xlsx",
        "dimensions": doc_dir / "dimensions.json",
        "audit": doc_dir / "audit_report.json",
        "crops": doc_dir / "crops",
    }


def _download_button(label: str, path: Path, mime: str) -> None:
    if path.exists():
        st.download_button(label, path.read_bytes(), file_name=path.name, mime=mime, use_container_width=True)


def _run_extraction(uploaded_file, ocr_engine: str, vlm_verifier: str) -> dict:
    safe_name = Path(uploaded_file.name).name
    run_dir = Path("output/cloud_runs") / _timestamp()
    run_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf", dir=run_dir) as handle:
        handle.write(uploaded_file.getbuffer())
        pdf_path = Path(handle.name)
    final_pdf_path = run_dir / safe_name
    pdf_path.replace(final_pdf_path)

    result = extract_pdf(final_pdf_path, run_dir, ocr_engine=ocr_engine, vlm_verifier=vlm_verifier)
    paths = _artifact_paths(run_dir, final_pdf_path, result.part_number)
    return {"result": result, "paths": paths, "run_dir": run_dir}


st.title("CAD Dimension Extractor")
st.caption("Geometry-first CAD dimension extraction with OCR crops, deterministic validation, and review-ready exports.")
if HOME_IMAGE_PATH.exists():
    st.image(str(HOME_IMAGE_PATH), use_container_width=True)

with st.sidebar:
    st.header("Extraction")
    ocr_engine = st.selectbox(
        "OCR engine",
        ["auto", "tesseract", "legacy", "paddle"],
        index=0,
        help="Auto uses PaddleOCR if installed, otherwise cropped Tesseract. Legacy uses full-page Tesseract.",
    )
    vlm_verifier = st.selectbox(
        "VLM verifier",
        ["disabled", "qwen", "donut", "openai"],
        index=0,
        help="Optional review-only crop verifier. Disabled is safest for free cloud.",
    )
    st.info("Unknown-template rows stay in review or rejected. Only template-confirmed rows are auto-accepted.")

uploaded_file = st.file_uploader("Upload a plotted CAD PDF", type=["pdf"])

if uploaded_file is None:
    st.write("Upload a CAD PDF to generate Excel, JSON, audit report, and crop snapshots.")
    st.stop()
    raise SystemExit

if st.button("Extract dimensions", type="primary", use_container_width=True):
    with st.spinner("Rendering PDF, detecting regions, running OCR, and validating dimensions..."):
        try:
            st.session_state["last_run"] = _run_extraction(uploaded_file, ocr_engine, vlm_verifier)
        except Exception as exc:
            st.error("Extraction failed.")
            st.exception(exc)

run_state = st.session_state.get("last_run")
if not run_state:
    st.stop()
    raise SystemExit

result = run_state["result"]
paths = run_state["paths"]
rows = result.rows
counts = _status_counts(rows)
audit = _read_json(paths["audit"])

st.subheader("Run Summary")
cols = st.columns(6)
cols[0].metric("Part", result.part_number or "Unknown")
cols[1].metric("Rows", len(rows))
cols[2].metric("Accepted", counts["accepted"])
cols[3].metric("Review", counts["review"])
cols[4].metric("Rejected", counts["rejected"])
cols[5].metric("Mode", result.mode)

metadata = audit.get("extraction_metadata", {})
if metadata:
    st.json(metadata, expanded=False)

st.subheader("Dimension Rows")
if rows:
    df = pd.DataFrame(rows)
    display_columns = [column for column in OUTPUT_COLUMNS + ["status", "source", "rejection_reason"] if column in df.columns]
    st.dataframe(df[display_columns], use_container_width=True, hide_index=True)
else:
    st.warning("No dimension rows were parsed. Try `legacy` OCR for comparison, or use PaddleOCR locally for better crop recognition.")

st.subheader("Exports")
export_cols = st.columns(3)
with export_cols[0]:
    _download_button("Download Excel", paths["xlsx"], "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
with export_cols[1]:
    _download_button("Download dimensions.json", paths["dimensions"], "application/json")
with export_cols[2]:
    _download_button("Download audit_report.json", paths["audit"], "application/json")

st.subheader("Crop Review")
crop_paths = sorted(paths["crops"].glob("*.png")) if paths["crops"].exists() else []
if not crop_paths:
    st.caption("No crop snapshots were generated for this run.")
else:
    preview_count = st.slider("Crop previews", min_value=1, max_value=min(24, len(crop_paths)), value=min(8, len(crop_paths)))
    grid = st.columns(4)
    for index, crop_path in enumerate(crop_paths[:preview_count]):
        with grid[index % 4]:
            st.image(str(crop_path), caption=crop_path.name, use_container_width=True)
