from __future__ import annotations

import io

def extract_text(pdf_bytes: bytes) -> str:
    try:
        import fitz
    except ImportError as exc:
        raise ImportError(
            "PyMuPDF es necesario para extraer texto de PDFs. "
            "Instálalo con: pip install pymupdf"
        ) from exc

    try:
        doc = fitz.open(stream=io.BytesIO(pdf_bytes), filetype = "pdf")
    except Exception as exc:
        raise RuntimeError(f"No se puede abrir el PDF: {exc}") from exc

    try:
        pages = [page.get_text() for page in doc]
    finally:
        doc.close()

    return "\n\n".join(pages)