from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


GRID_ROWS = list("ABCDEFGH")
GRID_COLS = list(range(1, 11))


def detect_grid_intervals(image_path: Path) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    gray = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if gray is None:
        raise RuntimeError(f"Cannot read image: {image_path}")

    _, ink = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)
    row_density = np.sum(ink > 0, axis=1)
    col_density = np.sum(ink > 0, axis=0)
    ys = np.where(row_density > gray.shape[1] * 0.25)[0]
    xs = np.where(col_density > gray.shape[0] * 0.25)[0]

    if len(xs) < 2 or len(ys) < 2:
        h, w = gray.shape
        x0, x1, y0, y1 = 0, w, 0, h
    else:
        x0, x1 = int(xs.min()), int(xs.max())
        y0, y1 = int(ys.min()), int(ys.max())

    col_edges = np.linspace(x0, x1, len(GRID_COLS) + 1)
    row_edges = np.linspace(y0, y1, len(GRID_ROWS) + 1)
    cols = [(int(col_edges[i]), int(col_edges[i + 1])) for i in range(len(GRID_COLS))]
    rows = [(int(row_edges[i]), int(row_edges[i + 1])) for i in range(len(GRID_ROWS))]
    return rows, cols


def zone_for_point(x: float, y: float, rows: list[tuple[int, int]], cols: list[tuple[int, int]]) -> str | None:
    row_idx = next((i for i, (a, b) in enumerate(rows) if a <= y < b), None)
    col_idx = next((i for i, (a, b) in enumerate(cols) if a <= x < b), None)
    if row_idx is None or col_idx is None:
        return None
    return f"{GRID_ROWS[row_idx]}{GRID_COLS[col_idx]}"
