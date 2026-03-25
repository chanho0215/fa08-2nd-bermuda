from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PDF_PATH = ROOT / "BERMUDA.pdf"
OUTPUT_DIR = ROOT / "docs" / "readme-assets" / "bermuda-pdf"

PAGES = [
    (13, "p13-eda-major-insights"),
    (18, "p18-final-model-performance"),
    (20, "p20-model-simulation"),
    (21, "p21-service-flow"),
    (22, "p22-system-architecture"),
    (23, "p23-data-flow-collection"),
    (24, "p24-data-flow-inference"),
]


def export_page(page_number: int, output_name: str) -> None:
    output_prefix = OUTPUT_DIR / output_name
    command = [
        "pdftoppm",
        "-png",
        "-f",
        str(page_number),
        "-l",
        str(page_number),
        "-singlefile",
        "-scale-to-x",
        "1920",
        "-scale-to-y",
        "-1",
        str(PDF_PATH),
        str(output_prefix),
    ]
    subprocess.run(command, check=True)


def main() -> None:
    if not PDF_PATH.exists():
        raise FileNotFoundError(f"Missing PDF: {PDF_PATH}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for page_number, output_name in PAGES:
        export_page(page_number, output_name)
        print(f"exported p.{page_number} -> {output_name}.png")


if __name__ == "__main__":
    main()
