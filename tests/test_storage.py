from __future__ import annotations

from pathlib import Path

from cad_dimensions.storage import LocalStore


def test_local_store_review_patch(tmp_path: Path) -> None:
    store = LocalStore(tmp_path / "app.sqlite3")
    store.insert_document("doc1", "drawing.pdf", tmp_path / "drawing.pdf", "4022.701.4430")
    store.replace_dimensions(
        "doc1",
        [
            {
                "dimension_id": "dim1",
                "Part Number": "4022.701.4430",
                "Zone": "A1",
                "Nominal Dimension": 10.0,
                "Tolerance": "+/-1",
                "Tolerance Value": 1.0,
                "Accuracy %": 80,
                "Multiplicity": "",
                "Lower Limit": 9.0,
                "Upper Limit": 11.0,
                "File Name": "drawing.pdf",
                "status": "review",
                "source": "ocr",
            }
        ],
    )

    updated = store.update_dimension("dim1", {"status": "accepted", "source": "human"})
    assert updated is not None
    assert updated["status"] == "accepted"
    assert store.list_dimensions("doc1")[0]["source"] == "human"
