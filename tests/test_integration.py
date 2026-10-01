import time
import uuid
import fitz
import numpy as np
import pytest
from pathlib import Path

from app.config import settings
from app.parsing import parse_pdf_document
from app.repository import DatabaseRepository
from app.retrieval import VectorIndex, BM25Index
from app.schemas import Chunk, QueryRequest
from app.rag import RAGService


@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_npn.db"
    repo = DatabaseRepository(db_path=str(db_file))
    return repo


@pytest.fixture
def synthetic_pdf(tmp_path):
    pdf_path = tmp_path / "test_report_94p.pdf"
    doc = fitz.open()
    for p in range(94):
        page = doc.new_page()
        page.insert_text((50, 50), f"Financial Section Page {p+1}", fontsize=16)
        page.insert_text((50, 90), f"Revenue Q{p%4+1}: {1000 + p*10} Lakhs. Net profit margin 15.5%.", fontsize=10)
    doc.save(str(pdf_path))
    doc.close()
    return str(pdf_path)


def test_9_pdf_ingestion_speed_contract(synthetic_pdf):
    """Integration test 9: 94-page PDF ingests in <20 seconds."""
    doc_id = str(uuid.uuid4())
    start_time = time.perf_counter()
    
    chunks = parse_pdf_document(synthetic_pdf, doc_id)
    elapsed = time.perf_counter() - start_time
    
    assert len(chunks) >= 94
    assert elapsed < 20.0  # Must ingest 94 pages in <20s


def test_10_retrieval_latency_contract():
    """Integration test 10: NumPy exact vector search latency is <100ms for 3000 vectors."""
    vec_index = VectorIndex(dim=384)
    # Generate 3,000 synthetic 384-dim vectors
    chunk_ids = [f"chunk_{i}" for i in range(3000)]
    vectors = np.random.randn(3000, 384).astype(np.float32)
    # L2 normalize
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    vectors = vectors / norms
    
    vec_index.add(chunk_ids, vectors)
    query_vec = vectors[42]  # sample query
    
    start_t = time.perf_counter()
    results = vec_index.search(query_vec, top_k=30)
    latency_ms = (time.perf_counter() - start_t) * 1000.0
    
    assert len(results) == 30
    assert results[0][0] == "chunk_42"
    assert latency_ms < 100.0  # Contract: <100ms


def test_11_integrity_gate_mismatch_catch(temp_db):
    """Integration test 11: Integrity gate catches chunk/vector mismatch."""
    doc_id = str(uuid.uuid4())
    temp_db.create_document(doc_id, "test.pdf", "application/pdf", 5, "path/to/test.pdf")
    
    c1 = Chunk("c1", doc_id, "test.pdf", 1, "Sec", "text", "t1", "ct1")
    c2 = Chunk("c2", doc_id, "test.pdf", 2, "Sec", "text", "t2", "ct2")
    vecs = np.random.randn(1, 384).astype(np.float32)  # Mismatch: 2 chunks but only 1 vector!
    
    # Manually insert 2 chunks but 1 vector
    with temp_db.get_connection() as conn:
        conn.execute("INSERT INTO chunks (id, document_id, filename, page_number, section, content_type, text, context_text) VALUES ('c1', ?, 'test.pdf', 1, 'Sec', 'text', 't1', 'ct1')", (doc_id,))
        conn.execute("INSERT INTO chunks (id, document_id, filename, page_number, section, content_type, text, context_text) VALUES ('c2', ?, 'test.pdf', 2, 'Sec', 'text', 't2', 'ct2')", (doc_id,))
        conn.execute("INSERT INTO vectors (chunk_id, dim, vector) VALUES ('c1', 384, ?)", (vecs[0].tobytes(),))
    
    is_valid = temp_db.check_integrity_gate(doc_id)
    assert is_valid is False  # Integrity gate MUST catch mismatch!


def test_12_sqlite_wal_mode_enabled(temp_db):
    """Integration test 12: SQLite DB runs in WAL mode."""
    with temp_db.get_connection() as conn:
        mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
        assert mode.lower() == "wal"


def test_13_end_to_end_parse_persist_retrieve(temp_db, tmp_path):
    """Integration test 13: End-to-end PDF parse, SQLite BLOB persist, and retrieval."""
    pdf_path = tmp_path / "sample.pdf"
    doc = fitz.open()
    p = doc.new_page()
    p.insert_text((50, 50), "Quarterly Financial Analysis Report Note 17", fontsize=14)
    p.insert_text((50, 80), "Operational EBITDA increased to 450 Million USD.", fontsize=10)
    doc.save(str(pdf_path))
    doc.close()

    doc_id = str(uuid.uuid4())
    temp_db.create_document(doc_id, "sample.pdf", "application/pdf", 1, str(pdf_path))
    chunks = parse_pdf_document(str(pdf_path), doc_id)
    vecs = np.random.randn(len(chunks), 384).astype(np.float32)
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    vecs = vecs / norms

    temp_db.insert_chunks_and_vectors(chunks, vecs)
    loaded_chunks = temp_db.load_all_chunks()
    loaded_cids, loaded_vecs = temp_db.load_all_vectors()

    assert len(loaded_chunks) == len(chunks)
    assert len(loaded_cids) == len(chunks)
    assert loaded_vecs.shape == vecs.shape


def test_14_conversation_history_persistence(temp_db):
    """Integration test 14: Conversations and messages are saved and retrieved correctly."""
    conv_id = str(uuid.uuid4())
    temp_db.create_conversation(conv_id)
    msg_id = str(uuid.uuid4())
    temp_db.add_message(msg_id, conv_id, "user", "What is the revenue?", ["c1", "c2"])

    conv = temp_db.get_conversation(conv_id)
    assert conv is not None
    assert len(conv.messages) == 1
    assert conv.messages[0].content == "What is the revenue?"
    assert conv.messages[0].sources == ["c1", "c2"]
