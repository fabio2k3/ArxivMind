"""
Test de extracción de PDF. En vez de depender de un archivo externo,
generamos un PDF mínimo en memoria con la propia librería PyMuPDF y
verificamos que extract_text() recupera el texto que insertamos.
"""

import pytest

fitz = pytest.importorskip("fitz")  # salta el test si pymupdf no está instalado

from backend.crawler.pdf_extractor import extract_text


def _make_test_pdf_bytes(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_extract_text_recovers_inserted_text():
    pdf_bytes = _make_test_pdf_bytes("Hello ArxivMind test")
    text = extract_text(pdf_bytes)
    assert "Hello ArxivMind test" in text


def test_extract_text_raises_on_corrupt_pdf():
    with pytest.raises(RuntimeError):
        extract_text(b"esto no es un PDF valido")
