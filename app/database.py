from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from .models import DocumentMeta

# Resolve a relative DATABASE_PATH against the project root (parent of app/),
# not the launcher's cwd — keeps the SQLite file inside the project no matter
# where uvicorn was started from.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_raw_db_path = os.environ.get("DATABASE_PATH", "./data/app.db")
DB_PATH = (
    _raw_db_path
    if os.path.isabs(_raw_db_path)
    else str((_PROJECT_ROOT / _raw_db_path).resolve())
)


def _connect() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                filename      TEXT NOT NULL,
                content_type  TEXT NOT NULL,
                size_bytes    INTEGER NOT NULL,
                text_content  TEXT NOT NULL,
                char_count    INTEGER NOT NULL,
                uploaded_at   TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS queries (
                id                     INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id            INTEGER,
                secondary_document_id  INTEGER,
                kind                   TEXT NOT NULL,
                question               TEXT,
                response_json          TEXT NOT NULL,
                created_at             TEXT NOT NULL,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
                FOREIGN KEY (secondary_document_id) REFERENCES documents(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_queries_doc ON queries(document_id);
            """
        )
        # Idempotent migration for an older DB created without secondary_document_id.
        cols = {row["name"] for row in conn.execute("PRAGMA table_info(queries)")}
        if "secondary_document_id" not in cols:
            conn.execute("ALTER TABLE queries ADD COLUMN secondary_document_id INTEGER")


def insert_document(
    filename: str, content_type: str, size_bytes: int, text_content: str
) -> DocumentMeta:
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO documents (filename, content_type, size_bytes, text_content, char_count, uploaded_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (filename, content_type, size_bytes, text_content, len(text_content), now),
        )
        doc_id = cur.lastrowid
    return DocumentMeta(
        id=doc_id,
        filename=filename,
        content_type=content_type,
        size_bytes=size_bytes,
        char_count=len(text_content),
        uploaded_at=datetime.fromisoformat(now),
    )


def get_document_text(doc_id: int) -> tuple[DocumentMeta, str] | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM documents WHERE id = ?", (doc_id,)
        ).fetchone()
    if row is None:
        return None
    meta = DocumentMeta(
        id=row["id"],
        filename=row["filename"],
        content_type=row["content_type"],
        size_bytes=row["size_bytes"],
        char_count=row["char_count"],
        uploaded_at=datetime.fromisoformat(row["uploaded_at"]),
    )
    return meta, row["text_content"]


def list_documents() -> list[DocumentMeta]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, filename, content_type, size_bytes, char_count, uploaded_at "
            "FROM documents ORDER BY id DESC"
        ).fetchall()
    return [
        DocumentMeta(
            id=r["id"],
            filename=r["filename"],
            content_type=r["content_type"],
            size_bytes=r["size_bytes"],
            char_count=r["char_count"],
            uploaded_at=datetime.fromisoformat(r["uploaded_at"]),
        )
        for r in rows
    ]


def record_query(
    document_id: int | None,
    kind: str,
    question: str | None,
    response_json: str,
    secondary_document_id: int | None = None,
) -> int:
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO queries (document_id, secondary_document_id, kind, question, response_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (document_id, secondary_document_id, kind, question, response_json, now),
        )
        return cur.lastrowid


def latest_compare(doc_id_before: int, doc_id_after: int) -> dict | None:
    """Most recent compare result for the given before/after pair, or None."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, document_id, secondary_document_id, kind, question, response_json, created_at "
            "FROM queries WHERE kind = 'compare' AND document_id = ? AND secondary_document_id = ? "
            "ORDER BY id DESC LIMIT 1",
            (doc_id_before, doc_id_after),
        ).fetchone()
    return dict(row) if row else None


def list_queries(document_id: int | None = None, limit: int = 100) -> list[dict]:
    sql = (
        "SELECT id, document_id, kind, question, response_json, created_at FROM queries"
    )
    params: tuple = ()
    if document_id is not None:
        sql += " WHERE document_id = ?"
        params = (document_id,)
    sql += " ORDER BY id DESC LIMIT ?"
    params = params + (limit,)
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def latest_query(document_id: int, kind: str) -> dict | None:
    """Most recent query of `kind` for `document_id`, or None.

    Used to make GET /summary/{id} and GET /requirements/{id} idempotent:
    the first GET runs the model and stores the result; subsequent GETs
    return the stored result.
    """
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, document_id, kind, question, response_json, created_at "
            "FROM queries WHERE document_id = ? AND kind = ? "
            "ORDER BY id DESC LIMIT 1",
            (document_id, kind),
        ).fetchone()
    return dict(row) if row else None
