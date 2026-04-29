from __future__ import annotations

from pathlib import Path


def _read_pdf_pages(path: Path) -> list[str]:
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError(
            "PyMuPDF is required for PDF extraction. Install parser dependencies first."
        ) from exc

    document = fitz.open(path)
    try:
        return [page.get_text("text") for page in document]
    finally:
        document.close()


def extract_pages(path: str | Path) -> list[str]:
    file_path = Path(path)
    suffix = file_path.suffix.lower()

    if suffix == ".pdf":
        return _read_pdf_pages(file_path)
    if suffix in {".txt", ".text"}:
        return [file_path.read_text(encoding="utf-8")]

    raise ValueError(f"Unsupported input type: {file_path.suffix}")
