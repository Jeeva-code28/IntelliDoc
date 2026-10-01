import sqlite3
import json
import numpy as np
from typing import List, Tuple, Dict, Optional, Any
from datetime import datetime
from app.config import settings
from app.schemas import Chunk, DocumentStatusResponse, MessageSchema, ConversationSchema


class DatabaseRepository:
    """
    SQLite DB Repository using WAL mode.
    Vectors stored as raw float32 BLOBs (1.5KB vs 22KB JSON).
    """

    def __init__(self, db_path: str = str(settings.DB_PATH)):
        self.db_path = db_path
        self._init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self.get_connection() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                filename TEXT,
                file_type TEXT,
                page_count INTEGER,
                status TEXT,
                progress REAL,
                error TEXT,
                created_at TIMESTAMP,
                metadata JSON,
                path TEXT
            );

            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY,
                document_id TEXT,
                filename TEXT,
                page_number INTEGER,
                section TEXT,
                content_type TEXT,
                text TEXT,
                context_text TEXT,
                bbox JSON,
                asset_path TEXT,
                temporal_start REAL,
                temporal_end REAL,
                metadata JSON,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS vectors (
                chunk_id TEXT PRIMARY KEY,
                dim INTEGER,
                vector BLOB,
                FOREIGN KEY (chunk_id) REFERENCES chunks(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                created_at TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT,
                role TEXT,
                content TEXT,
                sources JSON,
                created_at TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            );
            """)

    def clear_all(self):
        with self.get_connection() as conn:
            conn.execute("DELETE FROM messages;")
            conn.execute("DELETE FROM conversations;")
            conn.execute("DELETE FROM vectors;")
            conn.execute("DELETE FROM chunks;")
            conn.execute("DELETE FROM documents;")

    # Document CRUD Operations
    def create_document(self, doc_id: str, filename: str, file_type: str, page_count: int, file_path: str):
        now = datetime.utcnow().isoformat()
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO documents (id, filename, file_type, page_count, status, progress, error, created_at, metadata, path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (doc_id, filename, file_type, page_count, "processing", 0.0, None, now, json.dumps({}), file_path)
            )

    def update_document_progress(self, doc_id: str, progress: float, status: Optional[str] = None, error: Optional[str] = None):
        with self.get_connection() as conn:
            if status and error is not None:
                conn.execute(
                    "UPDATE documents SET progress = ?, status = ?, error = ? WHERE id = ?",
                    (progress, status, error, doc_id)
                )
            elif status:
                conn.execute(
                    "UPDATE documents SET progress = ?, status = ? WHERE id = ?",
                    (progress, status, doc_id)
                )
            else:
                conn.execute(
                    "UPDATE documents SET progress = ? WHERE id = ?",
                    (progress, doc_id)
                )

    def update_document_status(self, doc_id: str, status: str, progress: Optional[float] = None, error: Optional[str] = None):
        with self.get_connection() as conn:
            if progress is not None and error is not None:
                conn.execute(
                    "UPDATE documents SET status = ?, progress = ?, error = ? WHERE id = ?",
                    (status, progress, error, doc_id)
                )
            elif progress is not None:
                conn.execute(
                    "UPDATE documents SET status = ?, progress = ? WHERE id = ?",
                    (status, progress, doc_id)
                )
            elif error is not None:
                conn.execute(
                    "UPDATE documents SET status = ?, error = ? WHERE id = ?",
                    (status, error, doc_id)
                )
            else:
                conn.execute(
                    "UPDATE documents SET status = ? WHERE id = ?",
                    (status, doc_id)
                )

    def get_all_documents(self) -> List[DocumentStatusResponse]:
        return self.list_documents()

    def get_document(self, doc_id: str) -> Optional[DocumentStatusResponse]:
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
            if not row:
                return None
            return DocumentStatusResponse(
                id=row["id"],
                filename=row["filename"],
                file_type=row["file_type"],
                page_count=row["page_count"],
                status=row["status"],
                progress=row["progress"],
                error=row["error"],
                created_at=row["created_at"],
                path=row["path"]
            )

    def list_documents(self) -> List[DocumentStatusResponse]:
        with self.get_connection() as conn:
            rows = conn.execute("SELECT * FROM documents ORDER BY created_at DESC").fetchall()
            return [
                DocumentStatusResponse(
                    id=row["id"],
                    filename=row["filename"],
                    file_type=row["file_type"],
                    page_count=row["page_count"],
                    status=row["status"],
                    progress=row["progress"],
                    error=row["error"],
                    created_at=row["created_at"],
                    path=row["path"]
                ) for row in rows
            ]

    # Chunk & Vector CRUD
    def insert_chunks_and_vectors(self, chunks: List[Chunk], vectors: np.ndarray):
        """
        Stage 5 Persist: Stores chunks and vectors (raw float32 BLOBs) in batch transaction.
        """
        with self.get_connection() as conn:
            chunk_tuples = []
            vector_tuples = []
            for i, c in enumerate(chunks):
                vec_blob = vectors[i].astype(np.float32).tobytes()
                chunk_tuples.append((
                    c.id, c.document_id, c.filename, c.page_number, c.section,
                    c.content_type, c.text, c.context_text,
                    json.dumps(c.bbox) if c.bbox else None,
                    c.asset_path, c.temporal_start, c.temporal_end,
                    json.dumps(c.metadata)
                ))
                vector_tuples.append((c.id, settings.EMBEDDING_DIM, vec_blob))

            conn.executemany(
                """
                INSERT INTO chunks (id, document_id, filename, page_number, section, content_type, text, context_text, bbox, asset_path, temporal_start, temporal_end, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                chunk_tuples
            )
            conn.executemany(
                """
                INSERT INTO vectors (chunk_id, dim, vector)
                VALUES (?, ?, ?)
                """,
                vector_tuples
            )

    def load_all_chunks(self) -> List[Chunk]:
        with self.get_connection() as conn:
            rows = conn.execute("SELECT * FROM chunks").fetchall()
            chunks = []
            for r in rows:
                bbox = json.loads(r["bbox"]) if r["bbox"] else None
                metadata = json.loads(r["metadata"]) if r["metadata"] else {}
                chunks.append(Chunk(
                    id=r["id"],
                    document_id=r["document_id"],
                    filename=r["filename"],
                    page_number=r["page_number"],
                    section=r["section"],
                    content_type=r["content_type"],
                    text=r["text"],
                    context_text=r["context_text"],
                    bbox=tuple(bbox) if bbox else None,
                    asset_path=r["asset_path"],
                    temporal_start=r["temporal_start"],
                    temporal_end=r["temporal_end"],
                    metadata=metadata
                ))
            return chunks

    def load_all_vectors(self) -> Tuple[List[str], np.ndarray]:
        """
        Loads all float32 BLOB vectors into memory at startup for NumPy exact search.
        """
        with self.get_connection() as conn:
            rows = conn.execute("SELECT chunk_id, dim, vector FROM vectors").fetchall()
            chunk_ids = []
            vector_list = []
            for r in rows:
                chunk_ids.append(r["chunk_id"])
                vec = np.frombuffer(r["vector"], dtype=np.float32)
                vector_list.append(vec)
            if not vector_list:
                return [], np.empty((0, settings.EMBEDDING_DIM), dtype=np.float32)
            return chunk_ids, np.vstack(vector_list)

    def check_integrity_gate(self, doc_id: str) -> bool:
        """
        Stage 6 Integrity Gate: Assert count(chunks) == count(vectors) for a document.
        """
        with self.get_connection() as conn:
            chunk_count = conn.execute(
                "SELECT COUNT(*) as cnt FROM chunks WHERE document_id = ?", (doc_id,)
            ).fetchone()["cnt"]
            vector_count = conn.execute(
                "SELECT COUNT(*) as cnt FROM vectors WHERE chunk_id IN (SELECT id FROM chunks WHERE document_id = ?)", (doc_id,)
            ).fetchone()["cnt"]
            return chunk_count > 0 and chunk_count == vector_count

    # Conversations & Messages
    def create_conversation(self, conv_id: str) -> str:
        now = datetime.utcnow().isoformat()
        with self.get_connection() as conn:
            conn.execute(
                "INSERT INTO conversations (id, created_at) VALUES (?, ?)",
                (conv_id, now)
            )
        return conv_id

    def add_message(self, msg_id: str, conv_id: str, role: str, content: str, sources: List[str]):
        now = datetime.utcnow().isoformat()
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO messages (id, conversation_id, role, content, sources, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (msg_id, conv_id, role, content, json.dumps(sources), now)
            )

    def get_conversation(self, conv_id: str) -> Optional[ConversationSchema]:
        with self.get_connection() as conn:
            c_row = conn.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,)).fetchone()
            if not c_row:
                return None
            m_rows = conn.execute("SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC", (conv_id,)).fetchall()
            messages = [
                MessageSchema(
                    id=m["id"],
                    conversation_id=m["conversation_id"],
                    role=m["role"],
                    content=m["content"],
                    sources=json.loads(m["sources"]) if m["sources"] else [],
                    created_at=m["created_at"]
                ) for m in m_rows
            ]
            return ConversationSchema(id=c_row["id"], created_at=c_row["created_at"], messages=messages)


_db_repo = None


def get_repository() -> Any:
    global _db_repo
    if _db_repo is None:
        db_url = getattr(settings, "DATABASE_URL", "")
        if db_url.startswith("postgres://") or db_url.startswith("postgresql://"):
            from app.repository.postgres_repo import PostgresRepository
            _db_repo = PostgresRepository(db_url)
        else:
            _db_repo = DatabaseRepository()
    return _db_repo
