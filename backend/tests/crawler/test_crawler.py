"""
Tests del orquestador crawl(). Usamos monkeypatch para reemplazar
arxiv_client.search/download_pdf y pdf_extractor.extract_text por
versiones falsas — así el test corre instantáneo y no depende de que
arXiv esté disponible ni de respetar el rate limit real.
"""

import pytest

from backend.crawler import crawler
from backend.database.schema import init_db
from backend.database import document_repository as docs
from backend.database import chunk_repository as chunks_repo


FAKE_PAPERS = [
    {
        "arxiv_id": "1111.11111",
        "title": "Paper Uno",
        "authors": "Autor A",
        "abstract": "Abstract uno.",
        "categories": "cs.AI",
        "published": "2024-01-01T00:00:00Z",
        "updated": "2024-01-01T00:00:00Z",
        "pdf_url": "http://fake/pdf/1111.11111",
    },
    {
        "arxiv_id": "2222.22222",
        "title": "Paper Dos",
        "authors": "Autor B",
        "abstract": "Abstract dos.",
        "categories": "cs.LG",
        "published": "2024-01-02T00:00:00Z",
        "updated": "2024-01-02T00:00:00Z",
        "pdf_url": "http://fake/pdf/2222.22222",
    },
]


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "test_papers.db"
    init_db(path)
    return path


def test_crawl_happy_path(monkeypatch, db_path):
    monkeypatch.setattr(crawler.arxiv_client, "search", lambda query, max_results: FAKE_PAPERS)
    monkeypatch.setattr(crawler.arxiv_client, "download_pdf", lambda url: b"fake-pdf-bytes")
    monkeypatch.setattr(
        crawler,
        "extract_text",
        lambda pdf_bytes: "Esta es la primera oración del paper falso. "
                           "Esta es la segunda oración, con suficiente texto para formar un chunk válido.",
    )

    stats = crawler.crawl("cat:cs.AI", max_results=2, db_path=db_path)

    assert stats.papers_found == 2
    assert stats.papers_downloaded == 2
    assert stats.papers_failed == 0
    assert stats.chunks_created >= 2

    paper = docs.get_paper("1111.11111", db_path=db_path)
    assert paper["pdf_status"] == 1
    assert paper["title"] == "Paper Uno"

    chunks = chunks_repo.get_chunks("1111.11111", db_path=db_path)
    assert len(chunks) >= 1


def test_crawl_skips_already_downloaded_papers(monkeypatch, db_path):
    search_calls = {"count": 0}
    download_calls = {"count": 0}

    def fake_search(query, max_results):
        search_calls["count"] += 1
        return FAKE_PAPERS

    def fake_download(url):
        download_calls["count"] += 1
        return b"fake-pdf-bytes"

    monkeypatch.setattr(crawler.arxiv_client, "search", fake_search)
    monkeypatch.setattr(crawler.arxiv_client, "download_pdf", fake_download)
    monkeypatch.setattr(
        crawler, "extract_text",
        lambda pdf_bytes: "Oración de prueba suficientemente larga para ser un chunk válido completo.",
    )

    crawler.crawl("cat:cs.AI", max_results=2, db_path=db_path)
    assert download_calls["count"] == 2

    # Segunda corrida: los papers ya tienen pdf_status=1, no se deben
    # volver a descargar.
    stats2 = crawler.crawl("cat:cs.AI", max_results=2, db_path=db_path)
    assert stats2.papers_skipped == 2
    assert download_calls["count"] == 2  # sigue en 2, no subió


def test_crawl_handles_download_failure_gracefully(monkeypatch, db_path):
    monkeypatch.setattr(crawler.arxiv_client, "search", lambda query, max_results: FAKE_PAPERS[:1])

    def failing_download(url):
        raise ConnectionError("fallo simulado de red")

    monkeypatch.setattr(crawler.arxiv_client, "download_pdf", failing_download)

    stats = crawler.crawl("cat:cs.AI", max_results=1, db_path=db_path)

    assert stats.papers_failed == 1
    assert stats.papers_downloaded == 0

    paper = docs.get_paper("1111.11111", db_path=db_path)
    assert paper["pdf_status"] == 2
    assert "fallo simulado" in paper["index_error"]
