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


def render_first_page(input_path: Path, dpi: int = 300, output_dir: Path | None = None) -> Path:
    if input_path.suffix.lower() != ".pdf":
        return input_path
    output_image = (output_dir / f"{input_path.stem}.page1.png") if output_dir else input_path.with_suffix(".page1.png")
    if output_image.exists():
        return output_image
    legacy_output = Path("output/rendered") / f"{input_path.stem}.page1.png"
    if not output_dir and legacy_output.exists():
        return legacy_output
    if output_dir and legacy_output.exists():
        output_image.parent.mkdir(parents=True, exist_ok=True)
        try:
            import shutil

            shutil.copy2(legacy_output, output_image)
            return output_image
        except OSError:
            pass
    if convert_from_path is None:
        raise RuntimeError("pdf2image is not available. Install dependencies from requirements.txt.")
    poppler_path = find_poppler_path()
    if not poppler_path:
        raise RuntimeError("Poppler/pdftoppm is not available.")
    pages = convert_from_path(str(input_path), dpi=dpi, first_page=1, last_page=1, poppler_path=poppler_path)
    if not pages:
        raise RuntimeError(f"No pages rendered from {input_path}")
    output_image.parent.mkdir(parents=True, exist_ok=True)
    pages[0].save(output_image, "PNG")
    return output_image
