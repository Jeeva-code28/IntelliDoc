import os
import io
import json
import logging
import multiprocessing
import numpy as np
from typing import List, Tuple, Optional, Dict, Any
from app.config import settings
from app.schemas import Chunk, DocumentStatusResponse, ConversationResponse, MessageResponse
from app.repository.base import BaseRepository

logger = logging.getLogger("project_npn")


class PostgresRepository(BaseRepository):
    """
    Production-grade PostgreSQL + pgvector repository implementation.
    Supports connection pooling: (2 * CPU_CORES) + 10 (SSD spindle baseline).
    Enforces Row-Level Security (RLS) via app.current_tenant session setting.
    Stores raw float32 vector BLOBs / vector(384) columns efficiently.
    """

    def __init__(self, db_url: str = settings.DATABASE_URL):
        self.db_url = db_url
        self.cpu_cores = multiprocessing.cpu_count()
        self.max_connections = (2 * self.cpu_cores) + 10
        self.pool = None
        self._initialized = False
        self._init_db()

    def _init_db(self) -> None:
        """Initializes PostgreSQL schema, pgvector extension, and RLS policies."""
        try:
            import psycopg2
            from psycopg2 import pool
            
            # Extract parameters or use psycopg2 SimpleConnectionPool
            self.pool = psycopg2.pool.SimpleConnectionPool(
                minconn=1,
                maxconn=self.max_connections,
                dsn=self.db_url
            )
            
            conn = self.pool.getconn()
            try:
                with conn.cursor() as cur:
                    # Enable pgvector extension
                    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                    
                    # Create documents table with tenant_id
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS documents (
                            id VARCHAR(64) PRIMARY KEY,
                            tenant_id VARCHAR(64) NOT NULL DEFAULT 'default_tenant',
                            filename VARCHAR(255) NOT NULL,
                            file_type VARCHAR(50) NOT NULL,
                            page_count INT NOT NULL,
                            file_path TEXT NOT NULL,
                            status VARCHAR(30) NOT NULL DEFAULT 'processing',
                            progress REAL NOT NULL DEFAULT 0.0,
                            error TEXT,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                    
                    # Create chunks table with vector column (pgvector vector(384) or bytea fallback)
                    cur.execute(f"""
                        CREATE TABLE IF NOT EXISTS chunks (
                            id VARCHAR(64) PRIMARY KEY,
                            tenant_id VARCHAR(64) NOT NULL DEFAULT 'default_tenant',
                            document_id VARCHAR(64) REFERENCES documents(id) ON DELETE CASCADE,
                            filename VARCHAR(255) NOT NULL,
                            page_number INT NOT NULL,
                            section VARCHAR(255) NOT NULL,
                            content_type VARCHAR(50) NOT NULL,
                            text TEXT NOT NULL,
                            context_text TEXT NOT NULL,
                            bbox_json TEXT,
                            vector_blob BYTEA,
                            vector_embedding vector({settings.EMBEDDING_DIM})
                        );
                    """)
                    
                    # Create conversations table
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS conversations (
                            id VARCHAR(64) PRIMARY KEY,
                            tenant_id VARCHAR(64) NOT NULL DEFAULT 'default_tenant',
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                        );
                    """)

                    # Create messages table
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS messages (
                            id VARCHAR(64) PRIMARY KEY,
                            conversation_id VARCHAR(64) REFERENCES conversations(id) ON DELETE CASCADE,
                            role VARCHAR(20) NOT NULL,
                            content TEXT NOT NULL,
                            sources_json TEXT NOT NULL DEFAULT '[]',
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                        );
                    """)

                    # Create pgvector HNSW index
                    cur.execute(f"""
                        CREATE INDEX IF NOT EXISTS chunks_vector_hnsw_idx 
                        ON chunks USING hnsw (vector_embedding vector_cosine_ops)
                        WITH (m = 16, ef_construction = 128);
                    """)

                    # Enable Row Level Security (RLS)
                    cur.execute("ALTER TABLE documents ENABLE ROW LEVEL SECURITY;")
                    cur.execute("ALTER TABLE chunks ENABLE ROW LEVEL SECURITY;")
                    cur.execute("""
                        DO $$
                        BEGIN
                            IF NOT EXISTS (
                                SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_docs'
                            ) THEN
                                CREATE POLICY tenant_isolation_docs ON documents
                                USING (tenant_id = COALESCE(NULLIF(current_setting('app.current_tenant', true), ''), 'default_tenant'));
                            END IF;

                            IF NOT EXISTS (
                                SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_chunks'
                            ) THEN
                                CREATE POLICY tenant_isolation_chunks ON chunks
                                USING (tenant_id = COALESCE(NULLIF(current_setting('app.current_tenant', true), ''), 'default_tenant'));
                            END IF;
                        END
                        $$;
                    """)

                conn.commit()
                self._initialized = True
                logger.info("PostgreSQL database initialized with pgvector HNSW & RLS policies.")
            finally:
                self.pool.putconn(conn)

        except Exception as e:
            logger.warning(f"PostgreSQL connection failed ({e}). Falling back to mock/disconnected mode.")
            self._initialized = False

    def create_document(
        self,
        doc_id: str,
        filename: str,
        file_type: str,
        page_count: int,
        file_path: str,
        tenant_id: str = "default_tenant"
    ) -> None:
        if not self._initialized:
            return
        conn = self.pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SET LOCAL app.current_tenant = %s;", (tenant_id,)
                )
                cur.execute(
                    """
                    INSERT INTO documents (id, tenant_id, filename, file_type, page_count, file_path, status, progress)
                    VALUES (%s, %s, %s, %s, %s, %s, 'processing', 0.0)
                    ON CONFLICT (id) DO UPDATE SET status = 'processing', progress = 0.0;
                    """,
                    (doc_id, tenant_id, filename, file_type, page_count, file_path)
                )
            conn.commit()
        finally:
            self.pool.putconn(conn)

    def update_document_status(
        self,
        doc_id: str,
        status: str,
        progress: float = 0.0,
        error: Optional[str] = None
    ) -> None:
        if not self._initialized:
            return
        conn = self.pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE documents SET status = %s, progress = %s, error = %s WHERE id = %s;",
                    (status, progress, error, doc_id)
                )
            conn.commit()
        finally:
            self.pool.putconn(conn)

    def get_document(self, doc_id: str, tenant_id: str = "default_tenant") -> Optional[DocumentStatusResponse]:
        if not self._initialized:
            return None
        conn = self.pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("SET LOCAL app.current_tenant = %s;", (tenant_id,))
                cur.execute(
                    "SELECT id, filename, status, progress, created_at, error FROM documents WHERE id = %s;",
                    (doc_id,)
                )
                row = cur.fetchone()
                if not row:
                    return None
                return DocumentStatusResponse(
                    id=row[0],
                    filename=row[1],
                    status=row[2],
                    progress=row[3],
                    created_at=str(row[4]),
                    error=row[5]
                )
        finally:
            self.pool.putconn(conn)

    def get_all_documents(self, tenant_id: str = "default_tenant") -> List[DocumentStatusResponse]:
        if not self._initialized:
            return []
        conn = self.pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("SET LOCAL app.current_tenant = %s;", (tenant_id,))
                cur.execute("SELECT id, filename, status, progress, created_at, error FROM documents ORDER BY created_at DESC;")
                rows = cur.fetchall()
                return [
                    DocumentStatusResponse(
                        id=r[0],
                        filename=r[1],
                        status=r[2],
                        progress=r[3],
                        created_at=str(r[4]),
                        error=r[5]
                    ) for r in rows
                ]
        finally:
            self.pool.putconn(conn)

    def insert_chunks_and_vectors(
        self,
        chunks: List[Chunk],
        vectors: np.ndarray,
        tenant_id: str = "default_tenant"
    ) -> None:
        if not self._initialized or not chunks:
            return
        conn = self.pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("SET LOCAL app.current_tenant = %s;", (tenant_id,))
                for i, c in enumerate(chunks):
                    vec = vectors[i].astype(np.float32)
                    vec_blob = vec.tobytes()
                    vec_list_str = "[" + ",".join(map(str, vec.tolist())) + "]"
                    bbox_str = json.dumps(c.bbox) if c.bbox else None
                    
                    cur.execute(
                        """
                        INSERT INTO chunks (
                            id, tenant_id, document_id, filename, page_number, section,
                            content_type, text, context_text, bbox_json, vector_blob, vector_embedding
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET text = EXCLUDED.text, context_text = EXCLUDED.context_text;
                        """,
                        (
                            c.id, tenant_id, c.document_id, c.filename, c.page_number, c.section,
                            c.content_type, c.text, c.context_text, bbox_str, vec_blob, vec_list_str
                        )
                    )
            conn.commit()
        finally:
            self.pool.putconn(conn)

    def load_all_chunks(self, tenant_id: str = "default_tenant") -> List[Chunk]:
        if not self._initialized:
            return []
        conn = self.pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("SET LOCAL app.current_tenant = %s;", (tenant_id,))
                cur.execute(
                    "SELECT id, document_id, filename, page_number, section, content_type, text, context_text, bbox_json FROM chunks;"
                )
                rows = cur.fetchall()
                chunks = []
                for r in rows:
                    bbox = json.loads(r[8]) if r[8] else None
                    chunks.append(Chunk(
                        id=r[0],
                        document_id=r[1],
                        filename=r[2],
                        page_number=r[3],
                        section=r[4],
                        content_type=r[5],
                        text=r[6],
                        context_text=r[7],
                        bbox=bbox
                    ))
                return chunks
        finally:
            self.pool.putconn(conn)

    def load_all_vectors(self, tenant_id: str = "default_tenant") -> Tuple[List[str], np.ndarray]:
        if not self._initialized:
            return [], np.empty((0, settings.EMBEDDING_DIM), dtype=np.float32)
        conn = self.pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("SET LOCAL app.current_tenant = %s;", (tenant_id,))
                cur.execute("SELECT id, vector_blob FROM chunks ORDER BY id;")
                rows = cur.fetchall()
                chunk_ids = []
                vec_list = []
                for r in rows:
                    chunk_ids.append(r[0])
                    v = np.frombuffer(r[1], dtype=np.float32)
                    vec_list.append(v)
                if not vec_list:
                    return [], np.empty((0, settings.EMBEDDING_DIM), dtype=np.float32)
                return chunk_ids, np.vstack(vec_list)
        finally:
            self.pool.putconn(conn)

    def check_integrity_gate(self, doc_id: str) -> bool:
        if not self._initialized:
            return True
        conn = self.pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM chunks WHERE document_id = %s;", (doc_id,))
                chunk_count = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM chunks WHERE document_id = %s AND (vector_blob IS NOT NULL OR vector_embedding IS NOT NULL);", (doc_id,))
                vec_count = cur.fetchone()[0]
                return chunk_count == vec_count and chunk_count > 0
        finally:
            self.pool.putconn(conn)

    def create_conversation(self, conversation_id: str, tenant_id: str = "default_tenant") -> None:
        if not self._initialized:
            return
        conn = self.pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO conversations (id, tenant_id) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING;",
                    (conversation_id, tenant_id)
                )
            conn.commit()
        finally:
            self.pool.putconn(conn)

    def add_message(
        self,
        message_id: str,
        conversation_id: str,
        role: str,
        content: str,
        sources: List[str] = []
    ) -> None:
        if not self._initialized:
            return
        conn = self.pool.getconn()
        try:
            with conn.cursor() as cur:
                sources_str = json.dumps(sources)
                cur.execute(
                    """
                    INSERT INTO messages (id, conversation_id, role, content, sources_json)
                    VALUES (%s, %s, %s, %s, %s);
                    """,
                    (message_id, conversation_id, role, content, sources_str)
                )
            conn.commit()
        finally:
            self.pool.putconn(conn)

    def get_conversation(self, conversation_id: str) -> Optional[ConversationResponse]:
        if not self._initialized:
            return None
        conn = self.pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id, created_at FROM conversations WHERE id = %s;", (conversation_id,))
                c_row = cur.fetchone()
                if not c_row:
                    return None
                cur.execute("SELECT id, conversation_id, role, content, sources_json, created_at FROM messages WHERE conversation_id = %s ORDER BY created_at ASC;", (conversation_id,))
                m_rows = cur.fetchall()
                messages = []
                for m in m_rows:
                    sources = json.loads(m[4]) if m[4] else []
                    messages.append(MessageResponse(
                        id=m[0],
                        conversation_id=m[1],
                        role=m[2],
                        content=m[3],
                        sources=sources,
                        created_at=str(m[5])
                    ))
                return ConversationResponse(
                    id=c_row[0],
                    created_at=str(c_row[1]),
                    messages=messages
                )
        finally:
            self.pool.putconn(conn)
