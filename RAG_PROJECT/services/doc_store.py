"""SQLite metadata store for uploaded documents."""
import sqlite3
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

DB_PATH = Path(__file__).parent.parent / "data" / "users.db"


@dataclass
class DocMeta:
    doc_id: str
    filename: str
    chunk_count: int
    uploaded_at: float
    uploaded_by: str


def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _init_doc_table() -> None:
    with _get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                doc_id       TEXT PRIMARY KEY,
                filename     TEXT NOT NULL,
                chunk_count  INTEGER NOT NULL DEFAULT 0,
                uploaded_at  REAL NOT NULL,
                uploaded_by  TEXT NOT NULL
            )
            """
        )
        conn.commit()


def add_doc_meta(filename: str, chunk_count: int, uploaded_by: str) -> DocMeta:
    doc_id = str(uuid.uuid4())
    now = time.time()
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO documents (doc_id, filename, chunk_count, uploaded_at, uploaded_by) VALUES (?,?,?,?,?)",
            (doc_id, filename, chunk_count, now, uploaded_by),
        )
        conn.commit()
    return DocMeta(doc_id, filename, chunk_count, now, uploaded_by)


def list_docs() -> List[DocMeta]:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM documents ORDER BY uploaded_at DESC"
        ).fetchall()
    return [DocMeta(r["doc_id"], r["filename"], r["chunk_count"], r["uploaded_at"], r["uploaded_by"]) for r in rows]


def get_doc_meta(doc_id: str) -> Optional[DocMeta]:
    with _get_conn() as conn:
        row = conn.execute("SELECT * FROM documents WHERE doc_id=?", (doc_id,)).fetchone()
    if not row:
        return None
    return DocMeta(row["doc_id"], row["filename"], row["chunk_count"], row["uploaded_at"], row["uploaded_by"])


def delete_doc_meta(doc_id: str) -> bool:
    with _get_conn() as conn:
        cur = conn.execute("DELETE FROM documents WHERE doc_id=?", (doc_id,))
        conn.commit()
    return cur.rowcount > 0


_init_doc_table()
