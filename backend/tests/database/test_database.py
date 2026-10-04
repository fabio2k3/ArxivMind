"""
Tests de la Etapa 1 (database). Cada test crea su propia base de datos
temporal (fixture `db_path`) — ningún test depende de datos en disco ni
afecta a otro test.
"""

import pytest

from backend.database.schema import init_db, get_connection
from backend.database import document_repository as docs
from backend.database import chunk_repository as chunks


@pytest.fixture
def db_path(tmp_path):
    """Base de datos SQLite nueva y vacía, en un directorio temporal."""
    path = tmp_path / "test_papers.db"
    init_db(path)
    return path


def test_init_db_is_idempotent(db_path):
    # Llamar init_db() dos veces no debe fallar ni duplicar nada.
    init_db(db_path)
    init_db(db_path)


def test_upsert_and_get_paper(db_path):
    docs.upsert_paper(
        arxiv_id="2301.12345",
        title="Attention Is All You Need (ejemplo)",
        authors="A. Vaswani et al.",
        abstract="Proponemos una arquitectura basada solo en atención...",
        categories="cs.CL",
        db_path=db_path,
    )

    paper = docs.get_paper("2301.12345", db_path=db_path)
    assert paper is not None
    assert paper["title"] == "Attention Is All You Need (ejemplo)"
    assert paper["pdf_status"] == 0  # todavía no se descargó el PDF

    assert docs.paper_exists("2301.12345", db_path=db_path) is True
    assert docs.paper_exists("no-existe", db_path=db_path) is False


def test_upsert_paper_updates_existing_row(db_path):
    docs.upsert_paper(arxiv_id="2301.12345", title="Título viejo", db_path=db_path)
    docs.upsert_paper(arxiv_id="2301.12345", title="Título nuevo", db_path=db_path)

    paper = docs.get_paper("2301.12345", db_path=db_path)
    assert paper["title"] == "Título nuevo"

    with get_connection(db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
    assert count == 1  # no se duplicó la fila


def test_save_full_text_sets_status_ok(db_path):
    docs.upsert_paper(arxiv_id="2301.12345", title="Paper de prueba", db_path=db_path)
    docs.save_full_text("2301.12345", "Texto completo del paper...", db_path=db_path)

    paper = docs.get_paper("2301.12345", db_path=db_path)
    assert paper["pdf_status"] == 1
    assert paper["text_length"] == len("Texto completo del paper...")


def test_save_pdf_error_sets_status_error(db_path):
    docs.upsert_paper(arxiv_id="2301.12345", title="Paper de prueba", db_path=db_path)
    docs.save_pdf_error("2301.12345", "404 al descargar el PDF", db_path=db_path)

    paper = docs.get_paper("2301.12345", db_path=db_path)
    assert paper["pdf_status"] == 2
    assert "404" in paper["index_error"]


def test_get_pending_pdf_ids(db_path):
    docs.upsert_paper(arxiv_id="a", title="A", db_path=db_path)
    docs.upsert_paper(arxiv_id="b", title="B", db_path=db_path)
    docs.save_full_text("b", "ya tiene texto", db_path=db_path)  # b deja de estar pendiente

    pending = docs.get_pending_pdf_ids(db_path=db_path)
    assert pending == ["a"]


def test_save_and_get_chunks(db_path):
    docs.upsert_paper(arxiv_id="2301.12345", title="Paper de prueba", db_path=db_path)

    n = chunks.save_chunks(
        "2301.12345",
        ["Primer chunk de texto.", "Segundo chunk de texto.", "Tercer chunk."],
        db_path=db_path,
    )
    assert n == 3

    rows = chunks.get_chunks("2301.12345", db_path=db_path)
    assert len(rows) == 3
    assert [r["chunk_index"] for r in rows] == [0, 1, 2]
    assert rows[0]["text"] == "Primer chunk de texto."


def test_save_chunks_replaces_previous_chunks(db_path):
    docs.upsert_paper(arxiv_id="2301.12345", title="Paper de prueba", db_path=db_path)

    chunks.save_chunks("2301.12345", ["v1 chunk a", "v1 chunk b"], db_path=db_path)
    chunks.save_chunks("2301.12345", ["v2 chunk único"], db_path=db_path)  # re-crawl

    rows = chunks.get_chunks("2301.12345", db_path=db_path)
    assert len(rows) == 1
    assert rows[0]["text"] == "v2 chunk único"


def test_cascade_delete_removes_chunks(db_path):
    docs.upsert_paper(arxiv_id="2301.12345", title="Paper de prueba", db_path=db_path)
    chunks.save_chunks("2301.12345", ["chunk a", "chunk b"], db_path=db_path)

    with get_connection(db_path) as conn:
        conn.execute("DELETE FROM papers WHERE arxiv_id = ?", ("2301.12345",))

    assert chunks.get_chunks("2301.12345", db_path=db_path) == []


def test_stats(db_path):
    docs.upsert_paper(arxiv_id="a", title="A", db_path=db_path)
    docs.upsert_paper(arxiv_id="b", title="B", db_path=db_path)
    docs.save_full_text("a", "texto", db_path=db_path)
    chunks.save_chunks("a", ["chunk 1", "chunk 2"], db_path=db_path)

    paper_stats = docs.get_stats(db_path=db_path)
    assert paper_stats["total_papers"] == 2
    assert paper_stats["pdf_ok"] == 1
    assert paper_stats["pdf_pending"] == 1

    chunk_stats = chunks.get_chunk_stats(db_path=db_path)
    assert chunk_stats["total_chunks"] == 2
    assert chunk_stats["papers_with_chunks"] == 1
