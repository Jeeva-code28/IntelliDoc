import os
import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.schemas import QueryRequest, Chunk
from app.repository import get_repository
from app.rag import get_rag_service
from app.history import get_history_manager


@pytest.fixture
def client():
    return TestClient(app)


def test_conversation_deletion_and_history_archiving(client, tmp_path):
    repo = get_repository()
    rag = get_rag_service()
    rag.initialize_indexes()

    # 1. Create a dedicated test conversation
    conv_res = client.post("/api/conversations", json={"title": "Financial Deep Dive Q3"})
    assert conv_res.status_code == 200
    conv_id = conv_res.json()["id"]

    # 2. Ingest a test document into this conversation
    test_doc = tmp_path / "q3_revenue.txt"
    test_doc.write_text("Quarter 3 consolidated revenue amounted to 88.4 million dollars with operating margin of 24.1%.")
    doc_id = f"doc_q3_{conv_id[:8]}"

    ok = rag.ingest_document(str(test_doc), doc_id, "q3_revenue.txt", conversation_id=conv_id)
    assert ok is True

    # 3. Submit a query to generate prompts, replies, and citations
    q_res = client.post("/api/query", json={
        "query": "What is the Quarter 3 consolidated revenue and operating margin?",
        "conversation_id": conv_id
    })
    assert q_res.status_code == 200
    q_data = q_res.json()
    assert len(q_data["citations"]) > 0

    # Submit second query
    q_res2 = client.post("/api/query", json={
        "query": "What was the operating margin percentage?",
        "conversation_id": conv_id
    })
    assert q_res2.status_code == 200

    # Verify conversation has 4 messages (2 user, 2 assistant)
    conv_check = client.get(f"/api/conversations/{conv_id}").json()
    assert len(conv_check["messages"]) == 4
    assert len(conv_check["documents"]) == 1

    # 4. DELETE Conversation via API
    del_res = client.delete(f"/api/conversations/{conv_id}")
    assert del_res.status_code == 200
    del_data = del_res.json()
    assert del_data["success"] is True
    archive = del_data["archive"]
    assert archive is not None
    archive_id = archive["id"]

    # 5. Verify Export Files (.md and .json) exist in data/history
    md_path = Path(archive["md_file_path"])
    json_path = Path(archive["json_file_path"])
    assert md_path.exists()
    assert json_path.exists()

    md_content = md_path.read_text(encoding="utf-8")
    assert "Conversation Archive" in md_content
    assert "q3_revenue.txt" in md_content
    assert "Quarter 3 consolidated revenue" in md_content
    assert "operating margin" in md_content
    assert "Citations & Multimodal Evidence" in md_content

    json_content = json.loads(json_path.read_text(encoding="utf-8"))
    assert json_content["archive_id"] == archive_id
    assert json_content["conversation_id"] == conv_id
    assert len(json_content["messages"]) == 4
    assert len(json_content["documents"]) == 1
    # Check that assistant message contains citations
    asst_msg = next(m for m in json_content["messages"] if m["role"] == "assistant")
    assert len(asst_msg["sources"]) > 0
    assert asst_msg["sources"][0]["filename"] == "q3_revenue.txt"

    # 6. Verify Cascade Cleanup in active data
    # Conversation is gone from active list
    conv_list = client.get("/api/conversations").json()
    assert not any(c["id"] == conv_id for c in conv_list)

    # Repository documents for conv_id are 0
    docs = repo.get_all_documents(conversation_id=conv_id)
    assert len(docs) == 0

    # Vector store and BM25 index return 0 results for conv_id
    query_vec = rag.embedding_engine.embed_query("Quarter 3 revenue")
    dense_res = rag.vector_store.search(query_vec, k=10, conversation_id=conv_id)
    assert len(dense_res) == 0

    bm25_res = rag.bm25_index.search("revenue", top_k=10, conversation_id=conv_id)
    assert len(bm25_res) == 0

    # 7. Test History Endpoints
    # List history archives
    hist_list = client.get("/api/history").json()
    assert any(h["id"] == archive_id for h in hist_list)

    # Get history archive detail
    detail = client.get(f"/api/history/{archive_id}").json()
    assert detail["id"] == archive_id
    assert "markdown_content" in detail
    assert "q3_revenue.txt" in detail["markdown_content"]
    assert detail["json_data"] is not None

    # Download Markdown
    dl_md = client.get(f"/api/history/{archive_id}/download?format=md")
    assert dl_md.status_code == 200
    assert "text/markdown" in dl_md.headers["content-type"]
    assert "Conversation Archive" in dl_md.text

    # Download JSON
    dl_json = client.get(f"/api/history/{archive_id}/download?format=json")
    assert dl_json.status_code == 200
    assert "application/json" in dl_json.headers["content-type"]
    dl_json_data = json.loads(dl_json.text)
    assert dl_json_data["archive_id"] == archive_id

    # Delete single history archive
    del_hist = client.delete(f"/api/history/{archive_id}")
    assert del_hist.status_code == 200
    assert not md_path.exists()
    assert not json_path.exists()

    hist_after = client.get("/api/history").json()
    assert not any(h["id"] == archive_id for h in hist_after)
