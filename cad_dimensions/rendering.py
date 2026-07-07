from __future__ import annotations

import shutil
from pathlib import Path

try:
    from pdf2image import convert_from_path
except Exception:  # pragma: no cover
    convert_from_path = None


def find_poppler_path() -> str | None:
    exe = shutil.which("pdftoppm") or shutil.which("pdftoppm.exe")
    if exe:
        return str(Path(exe).parent)
    for candidate in ("/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/usr/local/opt/poppler/bin"):
        if (Path(candidate) / "pdftoppm").exists():
            return candidate
    return None


def render_first_page(input_path: Path, dpi: int = 300) -> Path:
    if input_path.suffix.lower() != ".pdf":
        return input_path
    if convert_from_path is None:
        raise RuntimeError("pdf2image is not available. Install dependencies from requirements.txt.")
    poppler_path = find_poppler_path()
    if not poppler_path:
        raise RuntimeError("Poppler/pdftoppm is not available.")
    output_image = input_path.with_suffix(".page1.png")
    if output_image.exists():
        return output_image
    pages = convert_from_path(str(input_path), dpi=dpi, first_page=1, last_page=1, poppler_path=poppler_path)
    if not pages:
        raise RuntimeError(f"No pages rendered from {input_path}")
    pages[0].save(output_image, "PNG")
    return output_image
