import os
import pytest
import pymupdf
import numpy as np
from pathlib import Path
from typing import List

from app.config import settings
from app.schemas import Chunk, QueryRequest
from app.repository import DatabaseRepository
from app.vector_store import NumpyVectorStore
from app.retrieval import BM25Index, rrf_fusion
from app.rag import RAGService


def create_test_pdf(file_path: Path, title: str, paragraphs: List[str]) -> str:
    """Creates a deterministic PDF with text using PyMuPDF."""
    doc = pymupdf.open()
    page = doc.new_page()
    y = 72
    page.insert_text((50, y), title, fontsize=16)
    y += 30
    for p in paragraphs:
        page.insert_text((50, y), p, fontsize=11)
        y += 24
    doc.save(str(file_path))
    doc.close()
    return str(file_path)


@pytest.fixture
def test_env(tmp_path):
    db_file = str(tmp_path / "isolation_test.db")
    repo = DatabaseRepository(db_path=db_file)
    vstore = NumpyVectorStore(dim=settings.EMBEDDING_DIM)
    rag = RAGService(repo=repo, vector_store=vstore)

    pdf_a_path = tmp_path / "pdf_a_orchid.pdf"
    create_test_pdf(
        pdf_a_path,
        "Confidential Project Orchid Dossier",
        [
            "Project Orchid Legacy Specification and Operations.",
            "Security token: LEGACY_CODE_731.",
            "Project Orchid achieved annual financial revenue of 145 million dollars in fiscal year 2023.",
            "Operating margins reached 32.5 percent across all European datacenter installations."
        ]
    )

    pdf_b_path = tmp_path / "pdf_b_cedar.pdf"
    create_test_pdf(
        pdf_b_path,
        "Current Project Cedar Executive Briefing",
        [
            "Project Cedar Modern Cloud Architecture and Microservices.",
            "Access authorization token: CURRENT_CODE_942.",
            "Project Cedar maintains zero trust security across 96 distributed cloud clusters.",
            "System availability SLA achieved 99.995 percent with Kubernetes auto-remediation."
        ]
    )

    return {
        "repo": repo,
        "vstore": vstore,
        "rag": rag,
        "pdf_a": str(pdf_a_path),
        "pdf_b": str(pdf_b_path),
        "tmp_path": tmp_path
    }


def test_1_query_pdf_b_returns_only_b_evidence(test_env):
    """Requirement 1: Querying PDF B returns only evidence from B."""
    rag = test_env["rag"]
    conv_id = "conv_scope_test"

    assert rag.ingest_document(test_env["pdf_a"], "doc_a", "pdf_a_orchid.pdf", conversation_id=conv_id) is True
    assert rag.ingest_document(test_env["pdf_b"], "doc_b", "pdf_b_cedar.pdf", conversation_id=conv_id) is True

    # Query with strict document scope = ["doc_b"]
    req = QueryRequest(
        query="What is the access authorization token for Project Cedar?",
        conversation_id=conv_id,
        document_ids=["doc_b"]
    )
    res = rag.query(req)

    assert "CURRENT_CODE_942" in res.answer
    assert "LEGACY_CODE_731" not in res.answer
    assert len(res.citations) > 0

    for cit in res.citations:
        assert cit.document_id == "doc_b", f"Pollution detected: citation document_id is {cit.document_id}"
        assert "pdf_b_cedar" in cit.filename
        chunk = rag.chunks_cache.get(cit.chunk_id)
        assert chunk is not None
        assert chunk.document_id == "doc_b"


def test_2_keyword_unique_to_a_not_returned_when_only_b_selected(test_env):
    """Requirement 2: A keyword unique to A is not returned when only B is selected."""
    rag = test_env["rag"]
    conv_id = "conv_keyword_test"

    rag.ingest_document(test_env["pdf_a"], "doc_a", "pdf_a_orchid.pdf", conversation_id=conv_id)
    rag.ingest_document(test_env["pdf_b"], "doc_b", "pdf_b_cedar.pdf", conversation_id=conv_id)

    # Ask specifically for Orchid legacy code, but restrict scope to doc_b
    req = QueryRequest(
        query="What is the LEGACY_CODE_731 security token for Project Orchid?",
        conversation_id=conv_id,
        document_ids=["doc_b"]
    )
    res = rag.query(req)

    # Must refuse or return no citations, and MUST NOT leak LEGACY_CODE_731 or doc_a chunks
    assert "LEGACY_CODE_731" not in res.answer or res.answer == "I cannot answer this based on the provided document."
    for cit in res.citations:
        assert cit.document_id == "doc_b"
        assert cit.document_id != "doc_a"


def test_3_query_for_info_missing_from_b_not_answered_using_a(test_env):
    """Requirement 3: A query for information missing from B is not answered using A."""
    rag = test_env["rag"]
    conv_id = "conv_missing_test"

    rag.ingest_document(test_env["pdf_a"], "doc_a", "pdf_a_orchid.pdf", conversation_id=conv_id)
    rag.ingest_document(test_env["pdf_b"], "doc_b", "pdf_b_cedar.pdf", conversation_id=conv_id)

    # Ask about fiscal year 2023 revenue (only in doc_a), scoping only to doc_b
    req = QueryRequest(
        query="What was the total financial revenue in fiscal year 2023?",
        conversation_id=conv_id,
        document_ids=["doc_b"]
    )
    res = rag.query(req)

    # Must NOT answer 145 million from doc_a
    assert "145 million" not in res.answer
    assert res.answer == "I cannot answer this based on the provided document." or len(res.citations) == 0
    assert not any(c.document_id == "doc_a" for c in res.citations)


def test_4_selecting_a_and_b_together_allows_evidence_from_both(test_env):
    """Requirement 4: Selecting A and B together allows evidence from both."""
    rag = test_env["rag"]
    conv_id = "conv_joint_test"

    rag.ingest_document(test_env["pdf_a"], "doc_a", "pdf_a_orchid.pdf", conversation_id=conv_id)
    rag.ingest_document(test_env["pdf_b"], "doc_b", "pdf_b_cedar.pdf", conversation_id=conv_id)

    # Query with both documents selected
    req = QueryRequest(
        query="What are the security keys and tokens for Project Orchid and Project Cedar?",
        conversation_id=conv_id,
        document_ids=["doc_a", "doc_b"]
    )
    res = rag.query(req)

    assert "LEGACY_CODE_731" in res.answer or "CURRENT_CODE_942" in res.answer
    cited_docs = {c.document_id for c in res.citations}
    assert cited_docs.issubset({"doc_a", "doc_b"})
    for cit in res.citations:
        assert cit.document_id in ["doc_a", "doc_b"]


def test_5_new_conversation_does_not_inherit_earlier_conversation(test_env):
    """Requirement 5: A new conversation selecting B does not inherit A from an earlier conversation."""
    rag = test_env["rag"]

    # Ingest doc_a in conv_1
    rag.ingest_document(test_env["pdf_a"], "doc_a", "pdf_a_orchid.pdf", conversation_id="conv_1")
    # Ingest doc_b in conv_2
    rag.ingest_document(test_env["pdf_b"], "doc_b", "pdf_b_cedar.pdf", conversation_id="conv_2")

    req = QueryRequest(
        query="What was the revenue and LEGACY_CODE_731?",
        conversation_id="conv_2",
        document_ids=["doc_b"]
    )
    res = rag.query(req)

    assert not any(c.document_id == "doc_a" for c in res.citations)
    assert "LEGACY_CODE_731" not in res.answer or res.answer == "I cannot answer this based on the provided document."


def test_6_bm25_cannot_introduce_out_of_scope_chunks(test_env):
    """Requirement 6: BM25 cannot introduce out-of-scope chunks."""
    rag = test_env["rag"]
    bm25 = rag.bm25_index

    # Add chunks from doc_a and doc_b
    chunks_a = [
        Chunk(id="a_chk_1", document_id="doc_a", filename="pdf_a.pdf", page_number=1,
              section="Spec", content_type="text", text="Orchid secret key LEGACY_CODE_731",
              context_text="Orchid secret key LEGACY_CODE_731", conversation_id="conv_bm25")
    ]
    chunks_b = [
        Chunk(id="b_chk_1", document_id="doc_b", filename="pdf_b.pdf", page_number=1,
              section="Spec", content_type="text", text="Cedar secret key CURRENT_CODE_942",
              context_text="Cedar secret key CURRENT_CODE_942", conversation_id="conv_bm25")
    ]
    bm25.add_chunks(chunks_a)
    bm25.add_chunks(chunks_b)

    # Search for term in A with scope restricted to doc_b -> must be empty
    results_scoped_b = bm25.search("LEGACY_CODE_731", top_k=10, document_ids=["doc_b"])
    assert len(results_scoped_b) == 0

    # Search for term in B with scope restricted to doc_a -> must be empty
    results_scoped_a = bm25.search("CURRENT_CODE_942", top_k=10, document_ids=["doc_a"])
    assert len(results_scoped_a) == 0

    # Search with scope doc_b -> only doc_b chunks returned
    results_valid = bm25.search("CURRENT_CODE_942", top_k=10, document_ids=["doc_b"])
    assert len(results_valid) == 1
    assert results_valid[0][0] == "b_chk_1"


def test_7_vector_search_cannot_introduce_out_of_scope_chunks(test_env):
    """Requirement 7: Vector search cannot introduce out-of-scope chunks."""
    vstore = test_env["vstore"]
    dim = settings.EMBEDDING_DIM

    v_a = np.ones((1, dim), dtype=np.float32)
    v_a = v_a / np.linalg.norm(v_a)

    v_b = np.full((1, dim), 2.0, dtype=np.float32)
    v_b = v_b / np.linalg.norm(v_b)

    chunk_a = Chunk(id="chk_vec_a", document_id="doc_a", filename="a.pdf", page_number=1,
                    section="A", content_type="text", text="text a", context_text="text a",
                    conversation_id="conv_v")
    chunk_b = Chunk(id="chk_vec_b", document_id="doc_b", filename="b.pdf", page_number=1,
                    section="B", content_type="text", text="text b", context_text="text b",
                    conversation_id="conv_v")

    vstore.upsert([chunk_a], v_a)
    vstore.upsert([chunk_b], v_b)

    query_vec = v_a[0]

    # Search restricted to doc_b: must never return chk_vec_a even if it is identical to query
    results_b = vstore.search(query_vec, k=10, document_ids=["doc_b"])
    returned_cids_b = [r[0] for r in results_b]
    assert "chk_vec_a" not in returned_cids_b
    assert returned_cids_b == ["chk_vec_b"]

    # Search restricted to doc_a: must never return chk_vec_b
    results_a = vstore.search(query_vec, k=10, document_ids=["doc_a"])
    returned_cids_a = [r[0] for r in results_a]
    assert "chk_vec_b" not in returned_cids_a
    assert returned_cids_a == ["chk_vec_a"]

    # Search restricted to non-existent doc: must return empty list
    results_none = vstore.search(query_vec, k=10, document_ids=["doc_nonexistent"])
    assert results_none == []


def test_8_rrf_cannot_reintroduce_filtered_candidates(test_env):
    """Requirement 8: RRF cannot reintroduce filtered candidates."""
    dense_scoped = [("b_chunk_1", 0.95), ("b_chunk_2", 0.82)]
    sparse_scoped = [("b_chunk_2", 12.4), ("b_chunk_1", 8.1)]

    fused = rrf_fusion(dense_scoped, sparse_scoped, k=60)
    fused_cids = [cid for cid, _ in fused]

    # Out of scope candidate "a_chunk_1" cannot exist in fused results
    assert "a_chunk_1" not in fused_cids
    assert set(fused_cids) == {"b_chunk_1", "b_chunk_2"}


def test_9_citations_always_refer_to_permitted_documents(test_env):
    """Requirement 9: Citations always refer to permitted documents."""
    rag = test_env["rag"]
    conv_id = "conv_cite_test"

    rag.ingest_document(test_env["pdf_a"], "doc_a", "pdf_a_orchid.pdf", conversation_id=conv_id)
    rag.ingest_document(test_env["pdf_b"], "doc_b", "pdf_b_cedar.pdf", conversation_id=conv_id)

    # Query with permitted scope = ["doc_b"]
    req = QueryRequest(
        query="Describe Project Cedar cloud architecture and cluster count.",
        conversation_id=conv_id,
        document_ids=["doc_b"]
    )
    res = rag.query(req)

    for cit in res.citations:
        assert cit.document_id == "doc_b"
        assert cit.document_id != "doc_a"
        chunk = rag.chunks_cache[cit.chunk_id]
        assert chunk.document_id == "doc_b"


def test_10_deleted_documents_cannot_appear_in_retrieval(test_env):
    """Requirement 10: Deleted documents cannot appear in retrieval."""
    rag = test_env["rag"]
    conv_id = "conv_del_test"

    rag.ingest_document(test_env["pdf_a"], "doc_a", "pdf_a_orchid.pdf", conversation_id=conv_id)
    rag.ingest_document(test_env["pdf_b"], "doc_b", "pdf_b_cedar.pdf", conversation_id=conv_id)

    # Delete doc_a
    assert rag.delete_document("doc_a") is True

    # Vector store must not have doc_a
    assert "doc_a" not in rag.vector_store.doc_id_map
    assert "doc_a" not in rag.vector_store.doc_index_map

    # BM25 must not have doc_a
    assert "doc_a" not in rag.bm25_index.doc_document_ids
    assert "doc_a" not in rag.bm25_index.doc_index_map

    # Querying for doc_a explicitly returns not found / invalid scope
    req_deleted = QueryRequest(
        query="What is LEGACY_CODE_731?",
        conversation_id=conv_id,
        document_ids=["doc_a"]
    )
    res_deleted = rag.query(req_deleted)
    assert "not found or has been deleted" in res_deleted.answer or "invalid_scope" in str(res_deleted.intent)
    assert len(res_deleted.citations) == 0

    # Querying conversation returns only doc_b
    req_conv = QueryRequest(
        query="What is the active access token?",
        conversation_id=conv_id
    )
    res_conv = rag.query(req_conv)
    assert all(c.document_id == "doc_b" for c in res_conv.citations)


def test_11_failed_or_partially_processed_documents_cannot_appear_as_ready(test_env):
    """Requirement 11: Failed or partially processed documents cannot appear as ready."""
    rag = test_env["rag"]
    repo = test_env["repo"]
    conv_id = "conv_status_test"

    repo.create_document("doc_proc", "processing.pdf", "application/pdf", 1, "path/proc.pdf", conversation_id=conv_id)
    repo.update_document_status("doc_proc", "processing", progress=0.4)

    repo.create_document("doc_fail", "failed.pdf", "application/pdf", 1, "path/fail.pdf", conversation_id=conv_id)
    repo.update_document_status("doc_fail", "failed", error="Corrupt byte stream")

    # Querying processing doc
    res_proc = rag.query(QueryRequest(
        query="What is in the processing document?",
        conversation_id=conv_id,
        document_ids=["doc_proc"]
    ))
    assert "still processing" in res_proc.answer
    assert len(res_proc.citations) == 0

    # Querying failed doc
    res_fail = rag.query(QueryRequest(
        query="What is in the failed document?",
        conversation_id=conv_id,
        document_ids=["doc_fail"]
    ))
    assert "failed indexing" in res_fail.answer
    assert len(res_fail.citations) == 0


def test_12_incremental_index_updates_preserve_chunk_vector_alignment(test_env):
    """Requirement 12: Incremental index updates preserve chunk/vector alignment."""
    vstore = test_env["vstore"]
    dim = settings.EMBEDDING_DIM

    # Generate 3 batches
    chunks_1 = [
        Chunk(id=f"c1_{i}", document_id="doc_1", filename="1.pdf", page_number=1,
              section="A", content_type="text", text=f"text 1 {i}", context_text=f"text 1 {i}")
        for i in range(5)
    ]
    vecs_1 = np.ones((5, dim), dtype=np.float32)

    chunks_2 = [
        Chunk(id=f"c2_{i}", document_id="doc_2", filename="2.pdf", page_number=1,
              section="B", content_type="text", text=f"text 2 {i}", context_text=f"text 2 {i}")
        for i in range(5)
    ]
    vecs_2 = np.full((5, dim), 2.0, dtype=np.float32)

    chunks_3 = [
        Chunk(id=f"c3_{i}", document_id="doc_3", filename="3.pdf", page_number=1,
              section="C", content_type="text", text=f"text 3 {i}", context_text=f"text 3 {i}")
        for i in range(5)
    ]
    vecs_3 = np.full((5, dim), 3.0, dtype=np.float32)

    vstore.upsert(chunks_1, vecs_1)
    vstore.upsert(chunks_2, vecs_2)
    vstore.upsert(chunks_3, vecs_3)

    assert vstore.matrix.shape[0] == 15
    assert len(vstore.chunk_ids) == 15
    assert len(vstore.doc_id_map) == 15

    # Delete doc_2 in the middle
    vstore.delete("doc_2")

    assert vstore.matrix.shape[0] == 10
    assert len(vstore.chunk_ids) == 10
    assert len(vstore.doc_id_map) == 10
    assert "doc_2" not in vstore.doc_id_map
    assert "doc_2" not in vstore.doc_index_map

    # Verify alignment of remaining chunks
    for idx, cid in enumerate(vstore.chunk_ids):
        if cid.startswith("c1_"):
            assert vstore.doc_id_map[idx] == "doc_1"
            assert np.allclose(vstore.matrix[idx], 1.0)
        elif cid.startswith("c3_"):
            assert vstore.doc_id_map[idx] == "doc_3"
            assert np.allclose(vstore.matrix[idx], 3.0)

    # Ingest doc_4 incrementally
    chunks_4 = [
        Chunk(id=f"c4_{i}", document_id="doc_4", filename="4.pdf", page_number=1,
              section="D", content_type="text", text=f"text 4 {i}", context_text=f"text 4 {i}")
        for i in range(4)
    ]
    vecs_4 = np.full((4, dim), 4.0, dtype=np.float32)
    vstore.upsert(chunks_4, vecs_4)

    assert vstore.matrix.shape[0] == 14
    assert len(vstore.chunk_ids) == 14
    assert len(vstore.doc_index_map["doc_4"]) == 4

    # Search scoped to doc_4
    res_4 = vstore.search(vecs_4[0], k=10, document_ids=["doc_4"])
    assert len(res_4) == 4
    assert all(cid.startswith("c4_") for cid, _ in res_4)
