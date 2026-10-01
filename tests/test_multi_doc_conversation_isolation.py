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
from app.multimedia import MultimediaProcessor


@pytest.fixture
def clean_repo(tmp_path):
    db_file = str(tmp_path / "multi_iso_test.db")
    repo = DatabaseRepository(db_path=db_file)
    return repo


def test_multi_document_per_conversation_isolation(clean_repo, tmp_path):
    """
    Test Goal:
    1. Conversation Alpha has 3 documents (financials, sales, marketing).
    2. Conversation Beta has 2 documents (server_specs, k8s_config).
    3. User queries Alpha -> gets answers referencing only Alpha documents.
    4. User queries Beta -> gets answers referencing only Beta documents.
    5. User queries Alpha with a query specific to Beta -> Zero spillover, refusal or no Beta chunks.
    6. User queries Beta with a query specific to Alpha -> Zero spillover, refusal or no Alpha chunks.
    """
    repo = clean_repo
    rag = RAGService(repo=repo)

    # Conversation Alpha Documents
    doc_a1 = tmp_path / "alpha_financials.txt"
    doc_a1.write_text("Project Alpha Financial Report: Q4 net profit reached 88.4 million dollars with operating margin 24.2%.")

    doc_a2 = tmp_path / "alpha_sales.txt"
    doc_a2.write_text("Project Alpha Sales Performance: Enterprise subscription sales reached 12,400 active client licenses.")

    doc_a3 = tmp_path / "alpha_marketing.txt"
    doc_a3.write_text("Project Alpha Marketing Metrics: Customer acquisition cost decreased by 18.5% year over year.")

    # Conversation Beta Documents
    doc_b1 = tmp_path / "beta_servers.txt"
    doc_b1.write_text("Project Beta Hardware Specification: Compute node clusters use AMD EPYC 9654 processors with 1.5TB DDR5 RAM.")

    doc_b2 = tmp_path / "beta_k8s.txt"
    doc_b2.write_text("Project Beta Kubernetes Architecture: Microservices are deployed across 48 pods with HPA threshold at 75% CPU.")

    # Ingest 3 docs into Conversation Alpha
    assert rag.ingest_document(str(doc_a1), "id_a1", "alpha_financials.txt", conversation_id="conv_alpha") is True
    assert rag.ingest_document(str(doc_a2), "id_a2", "alpha_sales.txt", conversation_id="conv_alpha") is True
    assert rag.ingest_document(str(doc_a3), "id_a3", "alpha_marketing.txt", conversation_id="conv_alpha") is True

    # Ingest 2 docs into Conversation Beta
    assert rag.ingest_document(str(doc_b1), "id_b1", "beta_servers.txt", conversation_id="conv_beta") is True
    assert rag.ingest_document(str(doc_b2), "id_b2", "beta_k8s.txt", conversation_id="conv_beta") is True

    # Verify repository counts per conversation
    docs_alpha = repo.list_documents(conversation_id="conv_alpha")
    assert len(docs_alpha) == 3
    alpha_filenames = {d.filename for d in docs_alpha}
    assert alpha_filenames == {"alpha_financials.txt", "alpha_sales.txt", "alpha_marketing.txt"}

    docs_beta = repo.list_documents(conversation_id="conv_beta")
    assert len(docs_beta) == 2
    beta_filenames = {d.filename for d in docs_beta}
    assert beta_filenames == {"beta_servers.txt", "beta_k8s.txt"}

    # Query Alpha about multiple Alpha topics (multi-doc retrieval within Alpha)
    q_alpha = rag.query(QueryRequest(
        query="What is the net profit and active client licenses for Alpha?",
        conversation_id="conv_alpha"
    ))
    assert q_alpha.answer != ""
    assert any("alpha_financials" in c.filename for c in q_alpha.citations) or any("alpha_sales" in c.filename for c in q_alpha.citations)
    # Zero spillover: No Beta files can be cited
    assert not any("beta" in c.filename for c in q_alpha.citations)

    # Query Beta about compute processors
    q_beta = rag.query(QueryRequest(
        query="What compute processors and RAM are used in the clusters?",
        conversation_id="conv_beta"
    ))
    assert q_beta.answer != ""
    assert any("beta_servers" in c.filename for c in q_beta.citations)
    # Zero spillover: No Alpha files can be cited
    assert not any("alpha" in c.filename for c in q_beta.citations)

    # Cross-conversation inquiry: Query Beta about Q4 net profit (Alpha knowledge)
    q_leak_check = rag.query(QueryRequest(
        query="What is the Q4 net profit for the project?",
        conversation_id="conv_beta"
    ))
    # Must NOT cite any Alpha documents
    assert not any("alpha" in c.filename for c in q_leak_check.citations)
    assert q_leak_check.answer == "I cannot answer this based on the provided document." or len(q_leak_check.citations) == 0


def test_conversation_resumption_and_incremental_upload(clean_repo, tmp_path):
    """
    Test Goal:
    1. Create Conversation A and upload Doc A1.
    2. Switch to Conversation B and upload Doc B1.
    3. Return to Conversation A and upload Doc A2.
    4. Verify Conversation A has exactly {Doc A1, Doc A2} and Conversation B has {Doc B1}.
    5. Query Conversation A -> retrieves from both Doc A1 and Doc A2, but strictly 0 from Doc B1.
    """
    repo = clean_repo
    rag = RAGService(repo=repo)

    doc_a1 = tmp_path / "plan_phase1.txt"
    doc_a1.write_text("Project Genesis Phase 1: Deploy identity server with Argon2id hashing and OIDC federation.")

    doc_b1 = tmp_path / "competitor_analysis.txt"
    doc_b1.write_text("Market Analysis: Competitor X launched enterprise pricing tier at 99 dollars per user.")

    # 1. Upload Doc A1 to conv_genesis
    assert rag.ingest_document(str(doc_a1), "id_gen1", "plan_phase1.txt", conversation_id="conv_genesis") is True

    # 2. Upload Doc B1 to conv_market
    assert rag.ingest_document(str(doc_b1), "id_mkt1", "competitor_analysis.txt", conversation_id="conv_market") is True

    # 3. Resume conv_genesis and upload Doc A2
    doc_a2 = tmp_path / "plan_phase2.txt"
    doc_a2.write_text("Project Genesis Phase 2: Roll out automated database replication with 3 read replicas.")
    assert rag.ingest_document(str(doc_a2), "id_gen2", "plan_phase2.txt", conversation_id="conv_genesis") is True

    # 4. Verify Document Lists
    docs_gen = repo.list_documents(conversation_id="conv_genesis")
    assert len(docs_gen) == 2
    assert {d.filename for d in docs_gen} == {"plan_phase1.txt", "plan_phase2.txt"}

    docs_mkt = repo.list_documents(conversation_id="conv_market")
    assert len(docs_mkt) == 1
    assert docs_mkt[0].filename == "competitor_analysis.txt"

    # 5. Query conv_genesis for Phase 2 topic
    q_gen = rag.query(QueryRequest(
        query="What is planned for Phase 2 database replication?",
        conversation_id="conv_genesis"
    ))
    assert any("plan_phase2" in c.filename for c in q_gen.citations)
    assert not any("competitor" in c.filename for c in q_gen.citations)

    # 6. Query conv_genesis for Phase 1 topic
    q_gen1 = rag.query(QueryRequest(
        query="What hashing algorithm is used in identity server for Phase 1?",
        conversation_id="conv_genesis"
    ))
    assert any("plan_phase1" in c.filename for c in q_gen1.citations)
    assert not any("competitor" in c.filename for c in q_gen1.citations)


def test_large_file_sliding_window_and_tabular_chunking(tmp_path):
    """
    Test Goal:
    Verify large text files and multi-row CSV files are chunked into complete sliding windows
    without truncating or dropping information.
    """
    multimedia = MultimediaProcessor()

    # Large text file with 10 sections
    sections = [f"=== SECTION {i} ===\nDetailed operational metrics and key findings for subsystem {i}. Value is {i * 1000} units.\n" * 15 for i in range(1, 11)]
    large_text = "\n".join(sections)
    text_file = tmp_path / "large_system_spec.txt"
    text_file.write_text(large_text)

    chunks = multimedia.process_text_document(str(text_file), "doc_large", "large_system_spec.txt", chunk_size=1200, overlap=200)
    assert len(chunks) > 5, f"Expected multiple sliding-window chunks for large text file, got {len(chunks)}"
    # Verify last section is represented in chunks
    assert any("SECTION 10" in c.text or "SECTION 10" in c.context_text for c in chunks)

    # Large CSV file with 120 rows
    csv_rows = ["TransactionID,Customer,Amount,Status,Region"]
    for i in range(1, 121):
        csv_rows.append(f"TXN_{i:04d},Customer_{i},{i * 25.50},Completed,Region_{i % 4}")
    csv_file = tmp_path / "large_transactions.csv"
    csv_file.write_text("\n".join(csv_rows))

    csv_chunks = multimedia.process_tabular_attachment(str(csv_file), "doc_csv", "large_transactions.csv")
    # With batch_size=40 and 120 rows, we should get 3 chunks
    assert len(csv_chunks) == 3, f"Expected 3 tabular chunks for 120 rows (40 rows/chunk), got {len(csv_chunks)}"
    assert "Rows 1-40" in csv_chunks[0].section
    assert "Rows 41-80" in csv_chunks[1].section
    assert "Rows 81-120" in csv_chunks[2].section
