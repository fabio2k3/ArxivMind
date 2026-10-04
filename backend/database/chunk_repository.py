from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from backend.database.schema import get_connection

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def save_chunks(arxid_id: str, texts: list[str], db_path: Optional[Path] = None) -> int:
    with get_connection(db_path) as conn:
        conn.execute("DELETE FROM chunks WHERE arxiv_id = ?", (arxid_id,))

        now = _now()

        rows = [
            (arxid_id, i, text, len(text), now)
            for i , text in enumerate(texts)
        ]
        conn.executemany(
            """
            INSERT INTO chunks(arxiv_id, chunk_index, text, char_count, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            rows,
        )
        return len(rows)

def get_chunks(arxid_id: str, db_path: Optional[Path] = None) -> list:
    with get_connection(db_path) as conn:
        return conn.execute(
            """
            SELECT * FROM chunks
            WHERE arxiv_id = ?
            ORDER BY chunk_index ASC
            """,
            (arxid_id,),
        ).fetchall()

def get_chunk_count(db_path: Optional[Path] = None) -> list:
    with get_connection(db_path) as conn:
        return conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]

def get_chunk_stats(db_path: Optional[Path] = None) -> list:
    with get_connection(db_path) as conn:
        total = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        papers_with_chunks = conn.execute("SELECT COUNT(DISTINCT arxid_id) FROM chunks").fetchone()[0]
        return {"total_chunks": total, "papers_with_chunks": papers_with_chunks}