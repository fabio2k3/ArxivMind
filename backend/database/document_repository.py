from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from backend.database.schema import get_connection

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def upsert_paper(
    arxiv_id: str,
    title: str,
    authors: Optional[str] = None,
    abstract: Optional[str]= None,
    categories: Optional[str] = None,
    published: Optional[str] = None,
    updated: Optional[str] = None,
    pdf_url: Optional[str] = None,
    db_path: Optional[Path] = None,        
) -> None:
    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO papers (arxiv_id, title, authors, abstract, categories,
                                 published, updated, pdf_url, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(arxiv_id) DO UPDATE SET
                title=excluded.title,
                authors=excluded.authors,
                abstract=excluded.abstract,
                categories=excluded.categories,
                published=excluded.published,
                updated=excluded.updated,
                pdf_url=excluded.pdf_url,
                fetched_at=excluded.fetched_at
            """,
            (arxiv_id, title, authors, abstract, categories,
             published, updated, pdf_url, _now()),
        )


def save_full_text(arxiv_id: str, full_text:str, db_path: Optional[Path] = None) -> None:
    with get_connection(db_path) as conn:
        conn.execute(
            """
            UPDATE papers
            SET full_text = ?, text_length = ?, pdf_status = 1, index_error = NULL
            WHERE arxiv_id = ?
            """,
            (full_text, len(full_text), arxiv_id),
        )

def save_pdf_error(arxiv_id:str, error: str, db_path: Optional[Path] = None) -> None:
    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE papers SET pdf_status = 2, index_error = ? WHERE arxiv_id = ?",
            (error, arxiv_id),
        )

def get_paper(arxiv_id:str,  db_path: Optional[Path] = None):
    with get_connection(db_path) as conn:
        return conn.execute(
            "SELECT * FROM papers WHERE arxiv_id = ?", (arxiv_id,)
        ).fetchone()

def paper_exists(arxiv_id:str,  db_path: Optional[Path] = None) -> bool:
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT 1 FROM papers WHERE arxiv_id = ?", (arxiv_id,)
        ).fetchone()
        return row is not None

def get_pending_pdf_ids(limit: int = 50, db_path: Optional[Path] = None) -> list[str]:
    """IDs de papers cuyo PDF todavía no se descargó (pdf_status=0)."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT arxiv_id FROM papers
            WHERE pdf_status = 0
            ORDER BY fetched_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [r["arxiv_id"] for r in rows]


def get_stats(db_path: Optional[Path] = None) -> dict:
    """Resumen rápido del estado de la tabla, útil para el orchestrator."""
    with get_connection(db_path) as conn:
        total = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
        ok = conn.execute(
            "SELECT COUNT(*) FROM papers WHERE pdf_status = 1"
        ).fetchone()[0]
        pending = conn.execute(
            "SELECT COUNT(*) FROM papers WHERE pdf_status = 0"
        ).fetchone()[0]
        errors = conn.execute(
            "SELECT COUNT(*) FROM papers WHERE pdf_status = 2"
        ).fetchone()[0]
        return {
            "total_papers": total,
            "pdf_ok": ok,
            "pdf_pending": pending,
            "pdf_errors": errors,
        }
