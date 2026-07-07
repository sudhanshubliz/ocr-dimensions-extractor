from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    file_name TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    part_number TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    status TEXT NOT NULL,
    output_dir TEXT,
    error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dimensions (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    row_json TEXT NOT NULL,
    status TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT,
    job_id TEXT,
    event TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class LocalStore:
    def __init__(self, db_path: Path = Path("cad_dimension_app.sqlite3")) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA)

    def insert_document(self, document_id: str, file_name: str, stored_path: Path, part_number: str = "") -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO documents (id, file_name, stored_path, part_number, created_at) VALUES (?, ?, ?, ?, ?)",
                (document_id, file_name, str(stored_path), part_number, utc_now()),
            )
        self.audit(document_id, None, "document_uploaded", {"file_name": file_name, "stored_path": str(stored_path)})

    def get_document(self, document_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
        return dict(row) if row else None

    def upsert_job(self, job_id: str, document_id: str, status: str, output_dir: Path | None = None, error: str = "") -> None:
        now = utc_now()
        with self.connect() as conn:
            exists = conn.execute("SELECT id FROM jobs WHERE id = ?", (job_id,)).fetchone()
            if exists:
                conn.execute(
                    "UPDATE jobs SET status = ?, output_dir = ?, error = ?, updated_at = ? WHERE id = ?",
                    (status, str(output_dir) if output_dir else None, error, now, job_id),
                )
            else:
                conn.execute(
                    "INSERT INTO jobs (id, document_id, status, output_dir, error, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (job_id, document_id, status, str(output_dir) if output_dir else None, error, now, now),
                )
        self.audit(document_id, job_id, "job_status", {"status": status, "error": error})

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return dict(row) if row else None

    def replace_dimensions(self, document_id: str, rows: list[dict[str, Any]]) -> None:
        now = utc_now()
        with self.connect() as conn:
            conn.execute("DELETE FROM dimensions WHERE document_id = ?", (document_id,))
            conn.executemany(
                "INSERT INTO dimensions (id, document_id, row_json, status, updated_at) VALUES (?, ?, ?, ?, ?)",
                [
                    (
                        row["dimension_id"],
                        document_id,
                        json.dumps(row, sort_keys=True),
                        row.get("status", "review"),
                        now,
                    )
                    for row in rows
                ],
            )
        self.audit(document_id, None, "dimensions_replaced", {"rows": len(rows)})

    def list_dimensions(self, document_id: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute("SELECT row_json FROM dimensions WHERE document_id = ? ORDER BY id", (document_id,)).fetchall()
        return [json.loads(row["row_json"]) for row in rows]

    def update_dimension(self, dimension_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
        with self.connect() as conn:
            existing = conn.execute("SELECT * FROM dimensions WHERE id = ?", (dimension_id,)).fetchone()
            if not existing:
                return None
            row = json.loads(existing["row_json"])
            row.update({key: value for key, value in patch.items() if value is not None})
            status = row.get("status", existing["status"])
            conn.execute(
                "UPDATE dimensions SET row_json = ?, status = ?, updated_at = ? WHERE id = ?",
                (json.dumps(row, sort_keys=True), status, utc_now(), dimension_id),
            )
        self.audit(existing["document_id"], None, "dimension_updated", {"dimension_id": dimension_id, "patch": patch})
        return row

    def audit(self, document_id: str | None, job_id: str | None, event: str, payload: dict[str, Any]) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO audit_logs (document_id, job_id, event, payload_json, created_at) VALUES (?, ?, ?, ?, ?)",
                (document_id, job_id, event, json.dumps(payload, sort_keys=True), utc_now()),
            )
