from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from backend.crawler import arxiv_client
from backend.crawler.chunker import make_chunks
from backend.crawler.pdf_extractor import extract_text
from backend.database import chunk_repository as chunks_repo
from backend.database import document_repository as docs

logger = logging.getLogger(__name__)


@dataclass
class CrawlStats:
    papers_found: int = 0
    papers_downloaded: int = 0
    papers_failed: int = 0
    papers_skipped: int = 0
    chunks_created: int = 0


def crawl(query: str, max_results: int = 10, db_path: Optional[Path] = None) -> CrawlStats:
    stats = CrawlStats()

    papers = arxiv_client.search(query, max_results=max_results)
    stats.papers_found = len(papers)
    logger.info("Encontrados %d papers para query=%r", len(papers), query)

    for meta in papers:
        docs.upsert_paper(db_path=db_path, **meta)

    for meta in papers:
        arxiv_id = meta["arxiv_id"]
        paper = docs.get_paper(arxiv_id, db_path=db_path)

        if paper["pdf_status"] == 1:
            stats.papers_skipped += 1
            continue

        try:
            pdf_bytes = arxiv_client.download_pdf(paper["pdf_url"])
            text = extract_text(pdf_bytes)
            docs.save_full_text(arxiv_id, text, db_path=db_path)

            text_chunks = make_chunks(text)
            n = chunks_repo.save_chunks(arxiv_id, text_chunks, db_path=db_path)

            stats.papers_downloaded += 1
            stats.chunks_created += n
            logger.info("OK %s -> %d chunks", arxiv_id, n)

        except Exception as exc:  
            docs.save_pdf_error(arxiv_id, str(exc), db_path=db_path)
            stats.papers_failed += 1
            logger.warning("FALLO %s: %s", arxiv_id, exc)

    return stats
