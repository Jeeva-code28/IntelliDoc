#!/usr/bin/env python3
"""
scripts/migrate_sqlite_to_postgres.py

Direct byte-copy migration script from SQLite BLOB vectors to PostgreSQL pgvector.
Exports float32 vector BLOBs and text chunks without re-embedding.
"""

import sys
import sqlite3
import logging
import argparse
import numpy as np
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from app.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("npn_migrate")


def migrate_data(sqlite_path: str, pg_url: str, tenant_id: str = "default_tenant") -> None:
    logger.info(f"Starting migration from SQLite ({sqlite_path}) to PostgreSQL ({pg_url})...")
    
    if not Path(sqlite_path).exists():
        logger.error(f"SQLite file does not exist at {sqlite_path}")
        sys.exit(1)

    try:
        import psycopg2
    except ImportError:
        logger.error("psycopg2 package is required for PostgreSQL migration. Install via pip install psycopg2-binary")
        sys.exit(1)

    sq_conn = sqlite3.connect(sqlite_path)
    sq_conn.row_factory = sqlite3.Row
    
    pg_conn = psycopg2.connect(pg_url)
    
    try:
        with pg_conn.cursor() as cur:
            # 1. Enable pgvector & create schema
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
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

            # 2. Migrate Documents
            sq_docs = sq_conn.execute("SELECT * FROM documents;").fetchall()
            logger.info(f"Migrating {len(sq_docs)} documents...")
            for doc in sq_docs:
                cur.execute(
                    """
                    INSERT INTO documents (id, tenant_id, filename, file_type, page_count, file_path, status, progress, error)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING;
                    """,
                    (
                        doc["id"], tenant_id, doc["filename"], doc["file_type"] or "pdf",
                        doc["page_count"] or 0, doc["path"] or "", doc["status"] or "completed",
                        doc["progress"] or 1.0, doc["error"]
                    )
                )

            # 3. Migrate Chunks & Vector BLOBs
            sq_chunks = sq_conn.execute("SELECT c.*, v.vector FROM chunks c LEFT JOIN vectors v ON c.id = v.chunk_id;").fetchall()
            logger.info(f"Migrating {len(sq_chunks)} chunks with raw float32 vectors...")
            
            migrated_count = 0
            for chunk in sq_chunks:
                vec_blob = chunk["vector"]
                vec_str = None
                if vec_blob:
                    vec = np.frombuffer(vec_blob, dtype=np.float32)
                    vec_str = "[" + ",".join(map(str, vec.tolist())) + "]"

                cur.execute(
                    """
                    INSERT INTO chunks (
                        id, tenant_id, document_id, filename, page_number, section,
                        content_type, text, context_text, bbox_json, vector_blob, vector_embedding
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING;
                    """,
                    (
                        chunk["id"], tenant_id, chunk["document_id"], chunk["filename"],
                        chunk["page_number"], chunk["section"], chunk["content_type"],
                        chunk["text"], chunk["context_text"], chunk["bbox"],
                        vec_blob, vec_str
                    )
                )
                migrated_count += 1

            # 4. Create HNSW index
            logger.info("Building HNSW vector index in PostgreSQL (m=16, ef_construction=128)...")
            cur.execute(f"""
                CREATE INDEX IF NOT EXISTS chunks_vector_hnsw_idx 
                ON chunks USING hnsw (vector_embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 128);
            """)

        pg_conn.commit()
        logger.info(f"Migration Complete! Successfully migrated {len(sq_docs)} documents and {migrated_count} chunks.")

    except Exception as e:
        pg_conn.rollback()
        logger.error(f"Migration failed with error: {e}")
        sys.exit(1)
    finally:
        sq_conn.close()
        pg_conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Direct byte-copy migration from SQLite to PostgreSQL + pgvector")
    parser.add_argument("--sqlite-path", type=str, default=str(settings.DB_PATH), help="Path to SQLite database file")
    parser.add_argument("--pg-url", type=str, default="postgresql://postgres:postgres@localhost:5432/npn_db", help="PostgreSQL connection string")
    parser.add_argument("--tenant-id", type=str, default="default_tenant", help="Tenant ID for RLS policies")
    args = parser.parse_args()

    migrate_data(args.sqlite_path, args.pg_url, args.tenant_id)
