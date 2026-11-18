"""A small SQLite store for documents and their text chunks (with optional embeddings)."""

import sqlite3
import threading
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id          TEXT PRIMARY KEY,
    filename    TEXT NOT NULL,
    pages       INTEGER NOT NULL,
    size_bytes  INTEGER NOT NULL,
    created_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS chunks (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id  TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page         INTEGER NOT NULL,
    position     INTEGER NOT NULL,
    text         TEXT NOT NULL,
    embedding    BLOB
);
CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(document_id);
"""


@dataclass
class Chunk:
    id: int
    document_id: str
    filename: str
    page: int
    text: str
    embedding: np.ndarray | None


class Store:
    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(SCHEMA)
        self._version = 0  # bumped on every write so caches know when to rebuild

    @property
    def version(self) -> int:
        return self._version

    @contextmanager
    def _tx(self):
        with self._lock:
            try:
                yield self._conn
                self._conn.commit()
                self._version += 1
            except Exception:
                self._conn.rollback()
                raise

    def add_document(
        self,
        filename: str,
        pages: int,
        size_bytes: int,
        chunks: list[tuple[int, str]],
        embeddings: list[list[float]] | None = None,
    ) -> str:
        doc_id = uuid.uuid4().hex[:12]
        now = datetime.now(UTC).isoformat()
        with self._tx() as conn:
            conn.execute(
                "INSERT INTO documents (id, filename, pages, size_bytes, created_at) VALUES (?,?,?,?,?)",
                (doc_id, filename, pages, size_bytes, now),
            )
            rows = []
            for i, (page, text) in enumerate(chunks):
                emb = None
                if embeddings is not None:
                    emb = np.asarray(embeddings[i], dtype=np.float32).tobytes()
                rows.append((doc_id, page, i, text, emb))
            conn.executemany(
                "INSERT INTO chunks (document_id, page, position, text, embedding) VALUES (?,?,?,?,?)",
                rows,
            )
        return doc_id

    def list_documents(self) -> list[dict]:
        cur = self._conn.execute(
            """SELECT d.*, COUNT(c.id) AS chunks FROM documents d
               LEFT JOIN chunks c ON c.document_id = d.id
               GROUP BY d.id ORDER BY d.created_at DESC"""
        )
        return [dict(r) for r in cur.fetchall()]

    def get_document(self, doc_id: str) -> dict | None:
        docs = [d for d in self.list_documents() if d["id"] == doc_id]
        return docs[0] if docs else None

    def delete_document(self, doc_id: str) -> bool:
        with self._tx() as conn:
            cur = conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            return cur.rowcount > 0

    def all_chunks(self) -> list[Chunk]:
        cur = self._conn.execute(
            """SELECT c.id, c.document_id, d.filename, c.page, c.text, c.embedding
               FROM chunks c JOIN documents d ON d.id = c.document_id
               ORDER BY c.document_id, c.position"""
        )
        out = []
        for r in cur.fetchall():
            emb = np.frombuffer(r["embedding"], dtype=np.float32) if r["embedding"] else None
            out.append(Chunk(r["id"], r["document_id"], r["filename"], r["page"], r["text"], emb))
        return out
