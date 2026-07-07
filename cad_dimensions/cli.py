from __future__ import annotations

import argparse
from pathlib import Path

from .export import write_dimensions_excel
from .pipeline import extract_many, extract_pdf


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract CAD dimensions using a grid-first hybrid workflow.")
    parser.add_argument("paths", nargs="+", type=Path, help="Input PDF(s), or input PDF plus output .xlsx for single-file mode")
    parser.add_argument("-o", "--output-dir", type=Path, default=Path("runs"), help="Output directory or run base directory")
    parser.add_argument("--flat-output", action="store_true", help="Write batch artifacts directly into --output-dir instead of a timestamped run folder")
    args = parser.parse_args()

    if len(args.paths) == 2 and args.paths[1].suffix.lower() == ".xlsx":
        result = extract_pdf(args.paths[0])
        write_dimensions_excel(result.rows, args.paths[1])
        print(f"Saved {len(result.rows)} rows to {args.paths[1]} ({result.mode})")
        return 0

    if len(args.paths) == 1:
        result = extract_pdf(args.paths[0], args.output_dir)
        print(f"Saved {len(result.rows)} rows to {result.run_dir or args.output_dir} ({result.mode})")
        return 0

    results, batch_output = extract_many(args.paths, args.output_dir, timestamped=not args.flat_output)
    print(f"Saved batch analysis to {batch_output}")
    for result in results:
        print(f"{result.input_path.name}: {len(result.rows)} rows, mode={result.mode}, part={result.part_number}")
    return 0
