from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .export import write_dimensions_excel
from .models import part_number_from_filename
from .pipeline import extract_pdf
from .storage import LocalStore


APP_ROOT = Path(".cad_dimension_app")
UPLOAD_DIR = Path("input/api_uploads")
RUN_DIR = Path("output/api_runs")
DB_PATH = APP_ROOT / "cad_dimension_app.sqlite3"

app = FastAPI(title="Local CAD Dimension Extraction API", version="0.1.0")
store = LocalStore(DB_PATH)


class DimensionPatch(BaseModel):
    zone: str | None = None
    nominal_dimension: float | None = None
    tolerance: str | None = None
    tolerance_value: float | None = None
    accuracy_percent: int | None = None
    multiplicity: int | str | None = None
    lower_limit: float | None = None
    upper_limit: float | None = None
    status: str | None = None
    rejection_reason: str | None = None
    source: str | None = "human"

    def to_row_patch(self) -> dict:
        mapping = {
            "zone": "Zone",
            "nominal_dimension": "Nominal Dimension",
            "tolerance": "Tolerance",
            "tolerance_value": "Tolerance Value",
            "accuracy_percent": "Accuracy %",
            "multiplicity": "Multiplicity",
            "lower_limit": "Lower Limit",
            "upper_limit": "Upper Limit",
            "status": "status",
            "rejection_reason": "rejection_reason",
            "source": "source",
        }
        return {target: getattr(self, source) for source, target in mapping.items() if getattr(self, source) is not None}


class ExtractRequest(BaseModel):
    ocr_engine: str = "auto"
    vlm_verifier: str = "disabled"


@app.post("/documents")
async def create_document(file: UploadFile = File(...)) -> dict:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported.")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    document_id = str(uuid4())
    stored_path = UPLOAD_DIR / f"{document_id}_{Path(file.filename).name}"
    with stored_path.open("wb") as handle:
        while chunk := await file.read(1024 * 1024):
            handle.write(chunk)
    part_number = part_number_from_filename(stored_path)
    store.insert_document(document_id, file.filename, stored_path, part_number)
    return {"id": document_id, "file_name": file.filename, "part_number": part_number}


@app.post("/documents/{document_id}/extract")
def extract_document(document_id: str, request: ExtractRequest | None = None) -> dict:
    request = request or ExtractRequest()
    document = store.get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    job_id = str(uuid4())
    output_dir = RUN_DIR / document_id
    store.upsert_job(job_id, document_id, "running", output_dir)
    try:
        result = extract_pdf(
            Path(document["stored_path"]),
            output_dir,
            ocr_engine=request.ocr_engine,
            vlm_verifier=request.vlm_verifier,
        )
        store.replace_dimensions(document_id, result.rows)
        store.upsert_job(job_id, document_id, "completed", output_dir)
    except Exception as exc:
        store.upsert_job(job_id, document_id, "failed", output_dir, str(exc))
        raise
    return {"job_id": job_id, "status": "completed", "rows": len(result.rows), "output_dir": str(output_dir)}


@app.get("/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


@app.get("/documents/{document_id}/dimensions")
def get_dimensions(document_id: str) -> dict:
    if not store.get_document(document_id):
        raise HTTPException(status_code=404, detail="Document not found.")
    return {"dimensions": store.list_dimensions(document_id)}


@app.patch("/dimensions/{dimension_id}")
def patch_dimension(dimension_id: str, patch: DimensionPatch) -> dict:
    updated = store.update_dimension(dimension_id, patch.to_row_patch())
    if not updated:
        raise HTTPException(status_code=404, detail="Dimension not found.")
    return updated


@app.post("/documents/{document_id}/export/xlsx")
def export_document_xlsx(document_id: str) -> FileResponse:
    document = store.get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    rows = [row for row in store.list_dimensions(document_id) if row.get("status") == "accepted"]
    output_path = RUN_DIR / document_id / "approved_dimensions.xlsx"
    write_dimensions_excel(rows, output_path)
    return FileResponse(output_path, filename=output_path.name)
