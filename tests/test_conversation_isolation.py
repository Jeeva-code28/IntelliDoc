import os
import pytest
import numpy as np
from pathlib import Path
from app.config import settings
from app.schemas import Chunk, QueryRequest
from app.repository import DatabaseRepository
from app.vector_store import NumpyVectorStore
from app.retrieval import BM25Index
from app.rag import RAGService


@pytest.fixture
def isolated_db(tmp_path):
    db_file = str(tmp_path / "test_iso.db")
    repo = DatabaseRepository(db_path=db_file)
    return repo


def test_vector_store_conversation_filtering():
    store = NumpyVectorStore(dim=4)
    v1 = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
    v2 = np.array([0.0, 1.0, 0.0, 0.0], dtype=np.float32)
    v3 = np.array([0.0, 0.0, 1.0, 0.0], dtype=np.float32)

    c1 = Chunk(id="c1", document_id="d1", filename="f1.pdf", page_number=1, section=None, content_type="text", text="alpha", context_text="alpha", conversation_id="conv_A")
    c2 = Chunk(id="c2", document_id="d2", filename="f2.pdf", page_number=1, section=None, content_type="text", text="beta", context_text="beta", conversation_id="conv_B")
    c3 = Chunk(id="c3", document_id="d3", filename="f3.pdf", page_number=1, section=None, content_type="text", text="gamma", context_text="gamma", conversation_id="conv_A")

    store.upsert([c1, c2, c3], np.vstack([v1, v2, v3]))

    # Search for v1 in conv_A
    res_A = store.search(v1, k=10, conversation_id="conv_A")
    chunk_ids_A = [cid for cid, _ in res_A]
    assert "c1" in chunk_ids_A
    assert "c3" in chunk_ids_A
    assert "c2" not in chunk_ids_A  # Zero spillover from conv_B!

    # Search for v2 in conv_B
    res_B = store.search(v2, k=10, conversation_id="conv_B")
    chunk_ids_B = [cid for cid, _ in res_B]
    assert "c2" in chunk_ids_B
    assert "c1" not in chunk_ids_B
    assert "c3" not in chunk_ids_B

    # Search in non-existent conversation returns empty
    res_C = store.search(v1, k=10, conversation_id="conv_empty")
    assert len(res_C) == 0


def test_bm25_conversation_filtering():
    bm25 = BM25Index()
    c1 = Chunk(id="c1", document_id="d1", filename="f1.pdf", page_number=1, section=None, content_type="text", text="apple revenue Q1 report", context_text="apple revenue", conversation_id="conv_1")
    c2 = Chunk(id="c2", document_id="d2", filename="f2.pdf", page_number=1, section=None, content_type="text", text="banana split ice cream recipe", context_text="banana recipe", conversation_id="conv_2")
    c3 = Chunk(id="c3", document_id="d3", filename="f3.pdf", page_number=1, section=None, content_type="text", text="apple pie dessert guide", context_text="apple pie", conversation_id="conv_1")

    bm25.add_chunks([c1, c2, c3])

    # Search apple in conv_1
    res1 = bm25.search("apple", top_k=5, conversation_id="conv_1")
    assert len(res1) == 2
    assert {cid for cid, _ in res1} == {"c1", "c3"}

    # Search apple in conv_2 (where it does not exist) -> must return empty
    res2 = bm25.search("apple", top_k=5, conversation_id="conv_2")
    assert len(res2) == 0

    # Search banana in conv_2
    res_banana = bm25.search("banana", top_k=5, conversation_id="conv_2")
    assert len(res_banana) == 1
    assert res_banana[0][0] == "c2"


def test_repository_conversation_partitioning(isolated_db):
    repo = isolated_db
    v_dim = settings.EMBEDDING_DIM
    v1 = np.ones((1, v_dim), dtype=np.float32)
    v2 = np.ones((1, v_dim), dtype=np.float32) * 2

    c1 = Chunk(id="chunk_1", document_id="doc_1", filename="doc1.pdf", page_number=1, section=None, content_type="text", text="Secret Project Alpha", context_text="Alpha", conversation_id="conv_finance")
    c2 = Chunk(id="chunk_2", document_id="doc_2", filename="doc2.pdf", page_number=1, section=None, content_type="text", text="Secret Project Beta", context_text="Beta", conversation_id="conv_engineering")

    repo.create_document("doc_1", "doc1.pdf", "application/pdf", 1, "/path/1", conversation_id="conv_finance")
    repo.create_document("doc_2", "doc2.pdf", "application/pdf", 1, "/path/2", conversation_id="conv_engineering")

    repo.insert_chunks_and_vectors([c1], v1, conversation_id="conv_finance")
    repo.insert_chunks_and_vectors([c2], v2, conversation_id="conv_engineering")

    # Verify document listing isolation
    docs_fin = repo.list_documents(conversation_id="conv_finance")
    assert len(docs_fin) == 1
    assert docs_fin[0].id == "doc_1"

    docs_eng = repo.list_documents(conversation_id="conv_engineering")
    assert len(docs_eng) == 1
    assert docs_eng[0].id == "doc_2"

    # Verify chunk loading isolation
    chunks_fin = repo.load_all_chunks(conversation_id="conv_finance")
    assert len(chunks_fin) == 1
    assert chunks_fin[0].id == "chunk_1"

    # Verify vector loading isolation
    ids_fin, _ = repo.load_all_vectors(conversation_id="conv_finance")
    assert ids_fin == ["chunk_1"]

    ids_eng, _ = repo.load_all_vectors(conversation_id="conv_engineering")
    assert ids_eng == ["chunk_2"]


def test_end_to_end_rag_zero_spillover(isolated_db, tmp_path):
    repo = isolated_db
    rag = RAGService(repo=repo)

    # Create 2 test text files
    file_a = tmp_path / "finances.txt"
    file_a.write_text("The net profit for Fiscal Year 2025 reached exactly 42.5 million dollars.")

    file_b = tmp_path / "engineering.txt"
    file_b.write_text("The internal turbine operates at a maximum temperature of 1450 Kelvin.")

    # Ingest file_a into conversation 1
    ok_a = rag.ingest_document(str(file_a), "doc_fin", "finances.txt", conversation_id="conv_001")
    assert ok_a is True

    # Ingest file_b into conversation 2
    ok_b = rag.ingest_document(str(file_b), "doc_eng", "engineering.txt", conversation_id="conv_002")
    assert ok_b is True

    # Query Conv 001 about profit -> Should cite finances.txt
    res_1 = rag.query(QueryRequest(query="What was the net profit for Fiscal Year 2025?", conversation_id="conv_001"))
    assert res_1.answer != ""
    assert any("42.5" in c.snippet or "finances" in c.filename for c in res_1.citations)
    assert not any("engineering" in c.filename for c in res_1.citations)

    # Query Conv 002 about profit -> ZERO knowledge in Conv 002 -> Refusal / Blocked
    res_2 = rag.query(QueryRequest(query="What was the net profit for Fiscal Year 2025?", conversation_id="conv_002"))
    assert not any("finances" in c.filename for c in res_2.citations)
    assert res_2.answer == "I cannot answer this based on the provided document." or "refusal" in res_2.answer.lower()

    # Query Conv 002 about turbine temperature -> Should cite engineering.txt
    res_3 = rag.query(QueryRequest(query="What is the maximum temperature of the internal turbine?", conversation_id="conv_002"))
    assert any("1450" in c.snippet or "engineering" in c.filename for c in res_3.citations)
    assert not any("finances" in c.filename for c in res_3.citations)

    # Resumption test: Return to Conv 001 and upload file_c (doc_bonus)
    file_c = tmp_path / "bonus.txt"
    file_c.write_text("Executive bonus allocation for 2025 is 3.2 million dollars.")
    ok_c = rag.ingest_document(str(file_c), "doc_bonus", "bonus.txt", conversation_id="conv_001")
    assert ok_c is True

    # Now Conv 001 knows about both finances.txt and bonus.txt, but still 0 knowledge of engineering.txt
    res_4 = rag.query(QueryRequest(query="What is the executive bonus allocation?", conversation_id="conv_001"))
    assert any("bonus" in c.filename for c in res_4.citations)
    assert not any("engineering" in c.filename for c in res_4.citations)
