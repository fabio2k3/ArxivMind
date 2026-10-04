from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "db" / "papers.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS papers (
    arxiv_id        TEXT PRIMARY KEY,            -- ej. "2301.12345"
    title           TEXT NOT NULL,
    authors         TEXT,
    abstract        TEXT,
    categories      TEXT,
    published       TEXT,                        -- fecha ISO-8601
    updated         TEXT,
    pdf_url         TEXT,
    fetched_at      TEXT NOT NULL,                -- cuándo se guardaron los metadatos
    full_text       TEXT,                         -- NULL hasta que se descargue el PDF
    text_length     INTEGER,
    pdf_status      INTEGER NOT NULL DEFAULT 0,   -- 0=pendiente 1=ok 2=error
    index_error     TEXT
);

CREATE INDEX IF NOT EXISTS idx_papers_categories ON papers(categories);
CREATE INDEX IF NOT EXISTS idx_papers_published  ON papers(published);
CREATE INDEX IF NOT EXISTS idx_papers_pdf_status ON papers(pdf_status);

CREATE TABLE IF NOT EXISTS chunks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    arxiv_id        TEXT NOT NULL REFERENCES papers(arxiv_id) ON DELETE CASCADE,
    chunk_index     INTEGER NOT NULL,             -- posición dentro del paper, 0-based
    text            TEXT NOT NULL,
    char_count      INTEGER NOT NULL,
    embedding       BLOB,                         -- se llena en la Etapa 6
    embedded_at     TEXT,
    created_at      TEXT NOT NULL,
    UNIQUE(arxiv_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS idx_chunks_arxiv_id    ON chunks(arxiv_id);
CREATE INDEX IF NOT EXISTS idx_chunks_embedded_at ON chunks(embedded_at);
"""


def init_db(db_path: Optional[Path] = None) -> None:
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(path)

    try:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(_SCHEMA)
        conn.commit()
    finally:
        conn.close()

@contextmanager
def get_connection(db_path: Optional[Path] = None) -> Iterator[sqlite3.Connection]:
    path = db_path or DB_PATH

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
