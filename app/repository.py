import sqlite3
import json
import numpy as np
from pathlib import Path
from typing import List, Tuple, Dict, Optional, Any
from datetime import datetime, timezone
from app.config import settings
from app.schemas import Chunk, DocumentStatusResponse, MessageSchema, ConversationSchema


class DatabaseRepository:
    """
    SQLite DB Repository using WAL mode.
    Vectors stored as raw float32 BLOBs (1.5KB vs 22KB JSON).
    Supports strict conversation-scoped multi-file knowledge bases.
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
                path TEXT,
                conversation_id TEXT
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
                conversation_id TEXT,
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
                title TEXT,
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

            CREATE TABLE IF NOT EXISTS history_archives (
                id TEXT PRIMARY KEY,
                conversation_id TEXT,
                title TEXT,
                created_at TIMESTAMP,
                deleted_at TIMESTAMP,
                message_count INTEGER,
                document_count INTEGER,
                md_file_path TEXT,
                json_file_path TEXT,
                transcript_summary TEXT
            );
            """)

            # Auto-migrations for existing databases
            try:
                conn.execute("ALTER TABLE documents ADD COLUMN conversation_id TEXT;")
            except Exception:
                pass
            try:
                conn.execute("ALTER TABLE chunks ADD COLUMN conversation_id TEXT;")
            except Exception:
                pass
            try:
                conn.execute("ALTER TABLE conversations ADD COLUMN title TEXT;")
            except Exception:
                pass

    def clear_all(self):
        with self.get_connection() as conn:
            conn.execute("DELETE FROM messages;")
            conn.execute("DELETE FROM conversations;")
            conn.execute("DELETE FROM vectors;")
            conn.execute("DELETE FROM chunks;")
            conn.execute("DELETE FROM documents;")

    # Document CRUD Operations
    def create_document(self, doc_id: str, filename: str, file_type: str, page_count: int, file_path: str, conversation_id: str = "default_conv"):
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            # Ensure conversation exists
            conn.execute(
                "INSERT OR IGNORE INTO conversations (id, title, created_at) VALUES (?, ?, ?)",
                (conversation_id, f"Chat - {filename[:25]}", now)
            )
            conn.execute(
                """
                INSERT INTO documents (id, filename, file_type, page_count, status, progress, error, created_at, metadata, path, conversation_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (doc_id, filename, file_type, page_count, "processing", 0.0, None, now, json.dumps({}), file_path, conversation_id)
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

    def update_document_metadata(self, doc_id: str, metadata: dict):
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE documents SET metadata = ? WHERE id = ?",
                (json.dumps(metadata), doc_id)
            )

    def get_all_documents(self, conversation_id: Optional[str] = None) -> List[DocumentStatusResponse]:
        return self.list_documents(conversation_id)

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
                path=row["path"],
                conversation_id=row["conversation_id"] if "conversation_id" in row.keys() else None,
                metadata=json.loads(row["metadata"]) if row["metadata"] else {}
            )

    def list_documents(self, conversation_id: Optional[str] = None) -> List[DocumentStatusResponse]:
        with self.get_connection() as conn:
            if conversation_id:
                rows = conn.execute(
                    "SELECT * FROM documents WHERE conversation_id = ? ORDER BY created_at DESC",
                    (conversation_id,)
                ).fetchall()
            else:
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
                    path=row["path"],
                    conversation_id=row["conversation_id"] if "conversation_id" in row.keys() else None,
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {}
                ) for row in rows
            ]

    # Chunk & Vector CRUD
    def insert_chunks_and_vectors(self, chunks: List[Chunk], vectors: np.ndarray, conversation_id: Optional[str] = None):
        """
        Stage 5 Persist: Stores chunks and vectors (raw float32 BLOBs) in batch transaction.
        """
        with self.get_connection() as conn:
            chunk_tuples = []
            vector_tuples = []
            for i, c in enumerate(chunks):
                vec_blob = vectors[i].astype(np.float32).tobytes()
                cid = getattr(c, "conversation_id", None) or conversation_id or c.metadata.get("conversation_id")
                chunk_tuples.append((
                    c.id, c.document_id, c.filename, c.page_number, c.section,
                    c.content_type, c.text, c.context_text,
                    json.dumps(c.bbox) if c.bbox else None,
                    c.asset_path, c.temporal_start, c.temporal_end,
                    json.dumps(c.metadata), cid
                ))
                vector_tuples.append((c.id, settings.EMBEDDING_DIM, vec_blob))

            conn.executemany(
                """
                INSERT INTO chunks (id, document_id, filename, page_number, section, content_type, text, context_text, bbox, asset_path, temporal_start, temporal_end, metadata, conversation_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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

    def load_all_chunks(self, conversation_id: Optional[str] = None) -> List[Chunk]:
        with self.get_connection() as conn:
            if conversation_id:
                rows = conn.execute("SELECT * FROM chunks WHERE conversation_id = ?", (conversation_id,)).fetchall()
            else:
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
                    conversation_id=r["conversation_id"] if "conversation_id" in r.keys() else None,
                    bbox=tuple(bbox) if bbox else None,
                    asset_path=r["asset_path"],
                    temporal_start=r["temporal_start"],
                    temporal_end=r["temporal_end"],
                    metadata=metadata
                ))
            return chunks

    def load_all_vectors(self, conversation_id: Optional[str] = None) -> Tuple[List[str], np.ndarray]:
        """
        Loads all float32 BLOB vectors into memory at startup for NumPy exact search.
        """
        with self.get_connection() as conn:
            if conversation_id:
                rows = conn.execute(
                    """
                    SELECT v.chunk_id, v.dim, v.vector 
                    FROM vectors v 
                    JOIN chunks c ON v.chunk_id = c.id 
                    WHERE c.conversation_id = ?
                    """,
                    (conversation_id,)
                ).fetchall()
            else:
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
    def create_conversation(self, conv_id: str, title: Optional[str] = None) -> str:
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO conversations (id, title, created_at) VALUES (?, ?, ?)",
                (conv_id, title or "New Conversation", now)
            )
        return conv_id

    def ensure_conversation(self, conv_id: str, title: Optional[str] = None) -> str:
        return self.create_conversation(conv_id, title)

    def list_conversations(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute("""
                SELECT 
                    c.id, 
                    COALESCE(c.title, 'New Conversation') as title, 
                    c.created_at,
                    COUNT(DISTINCT d.id) as document_count,
                    COUNT(DISTINCT m.id) as message_count
                FROM conversations c
                LEFT JOIN documents d ON d.conversation_id = c.id
                LEFT JOIN messages m ON m.conversation_id = c.id
                GROUP BY c.id
                ORDER BY c.created_at DESC
            """).fetchall()
            return [
                {
                    "id": r["id"],
                    "title": r["title"],
                    "created_at": r["created_at"],
                    "document_count": r["document_count"],
                    "message_count": r["message_count"]
                }
                for r in rows
            ]

    def add_message(self, msg_id: str, conv_id: str, role: str, content: str, sources: List[str]):
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            # Ensure conversation exists
            conn.execute(
                "INSERT OR IGNORE INTO conversations (id, title, created_at) VALUES (?, ?, ?)",
                (conv_id, "New Conversation", now)
            )
            # If user message, update title if default
            if role == "user":
                current = conn.execute("SELECT title FROM conversations WHERE id = ?", (conv_id,)).fetchone()
                if current and (current["title"] == "New Conversation" or not current["title"]):
                    clean_title = content.strip().replace("\n", " ")[:35]
                    conn.execute("UPDATE conversations SET title = ? WHERE id = ?", (clean_title, conv_id))

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
            d_rows = conn.execute("SELECT * FROM documents WHERE conversation_id = ? ORDER BY created_at DESC", (conv_id,)).fetchall()
            documents = [
                DocumentStatusResponse(
                    id=r["id"],
                    filename=r["filename"],
                    file_type=r["file_type"],
                    page_count=r["page_count"],
                    status=r["status"],
                    progress=r["progress"],
                    error=r["error"],
                    created_at=r["created_at"],
                    path=r["path"],
                    conversation_id=r["conversation_id"]
                ) for r in d_rows
            ]
            return ConversationSchema(
                id=c_row["id"],
                created_at=c_row["created_at"],
                title=c_row["title"] if "title" in c_row.keys() else "New Conversation",
                messages=messages,
                documents=documents
            )

    def delete_conversation(self, conv_id: str) -> bool:
        """
        Deletes a conversation and all its cascade-related data (messages, documents, chunks, vectors).
        """
        with self.get_connection() as conn:
            conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conv_id,))
            conn.execute(
                "DELETE FROM vectors WHERE chunk_id IN (SELECT id FROM chunks WHERE conversation_id = ?)",
                (conv_id,)
            )
            conn.execute("DELETE FROM chunks WHERE conversation_id = ?", (conv_id,))
            conn.execute("DELETE FROM documents WHERE conversation_id = ?", (conv_id,))
            conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
        return True

    def delete_document(self, doc_id: str) -> bool:
        """
        Deletes a document and its cascade-related data (chunks, vectors).
        """
        with self.get_connection() as conn:
            conn.execute(
                "DELETE FROM vectors WHERE chunk_id IN (SELECT id FROM chunks WHERE document_id = ?)",
                (doc_id,)
            )
            conn.execute("DELETE FROM chunks WHERE document_id = ?", (doc_id,))
            conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        return True

    # History Archive Operations
    def create_history_archive(self, record: Dict[str, Any]) -> str:
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO history_archives (
                    id, conversation_id, title, created_at, deleted_at,
                    message_count, document_count, md_file_path, json_file_path, transcript_summary
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["id"],
                    record["conversation_id"],
                    record["title"],
                    record["created_at"],
                    record["deleted_at"],
                    record["message_count"],
                    record["document_count"],
                    record["md_file_path"],
                    record["json_file_path"],
                    record.get("transcript_summary", "")
                )
            )
        return record["id"]

    def list_history_archives(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM history_archives ORDER BY deleted_at DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    def get_history_archive(self, history_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM history_archives WHERE id = ?", (history_id,)
            ).fetchone()
            if not row:
                return None
            return dict(row)

    def delete_history_archive(self, history_id: str) -> bool:
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM history_archives WHERE id = ?", (history_id,)).fetchone()
            if row:
                # Remove files on disk if they exist
                for f_key in ["md_file_path", "json_file_path"]:
                    p = row[f_key]
                    if p and Path(p).exists():
                        try:
                            Path(p).unlink()
                        except Exception:
                            pass
                conn.execute("DELETE FROM history_archives WHERE id = ?", (history_id,))
                return True
            return False

    def clear_all_history_archives(self) -> bool:
        with self.get_connection() as conn:
            rows = conn.execute("SELECT * FROM history_archives").fetchall()
            for row in rows:
                for f_key in ["md_file_path", "json_file_path"]:
                    p = row[f_key]
                    if p and Path(p).exists():
                        try:
                            Path(p).unlink()
                        except Exception:
                            pass
            conn.execute("DELETE FROM history_archives")
        return True


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
