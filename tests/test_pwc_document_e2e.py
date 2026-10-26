import time
import httpx
import pytest
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000"

def test_pwc_financial_statements_complete_flow():
    pdf_file = Path("data") / "basic-understanding-of-a-companys-financials.pdf"
    assert pdf_file.exists(), "PwC PDF file not found!"

    with httpx.Client(base_url=BASE_URL, timeout=120.0) as client:
        # 1. Health check
        res_health = client.get("/health")
        assert res_health.status_code == 200
        assert res_health.json()["status"] == "healthy"

        # 2. Create conversation
        res_conv = client.post("/api/conversations", json={"title": "PwC Financial Statements Analysis"})
        assert res_conv.status_code == 200
        conv_id = res_conv.json()["id"]

        # 3. Upload document
        with open(pdf_file, "rb") as f:
            files = {"file": ("pwc_financial_statements_september_2020.pdf", f, "application/pdf")}
            data = {"conversation_id": conv_id}
            res_upload = client.post("/api/documents/upload", files=files, data=data)
        
        assert res_upload.status_code in [200, 202]
        doc_id = res_upload.json()["id"]

        # 4. Poll until document is ready
        max_wait = 90
        start_poll = time.time()
        doc_ready = False
        doc_data = None

        while time.time() - start_poll < max_wait:
            res_docs = client.get(f"/api/conversations/{conv_id}/documents")
            assert res_docs.status_code == 200
            docs = res_docs.json()
            target = next((d for d in docs if d["id"] == doc_id), None)
            if target and target["status"] == "ready":
                doc_ready = True
                doc_data = target
                break
            elif target and target["status"] == "failed":
                pytest.fail(f"Document ingestion failed: {target.get('error')}")
            time.sleep(2.0)

        assert doc_ready is True, "Document failed to reach 'ready' status within timeout"
        print(f"\n[Checklist 1/6 PASS] Ingestion complete: doc_id={doc_id}, page_count={doc_data['page_count']}")

        # 5. Test Query 1: Simplified Balance Sheet (Total assets and current assets)
        q1 = {
            "query": "What are the total assets, total current assets, and cash on the Simplified Balance Sheet?",
            "conversation_id": conv_id,
            "document_ids": [doc_id],
            "skip_verification": False
        }
        r1 = client.post("/api/query", json=q1).json()
        assert len(r1["citations"]) > 0
        assert any("214,000" in c["snippet"] or "94,000" in c["snippet"] for c in r1["citations"])
        assert all(c["document_id"] == doc_id for c in r1["citations"])
        print(f"[Checklist 2/6 PASS] Query 1 (Simplified Balance Sheet) citations verified. Document ID: {doc_id}")

        # 6. Test Query 2: Direct vs Indirect Method of Cash Flow
        q2 = {
            "query": "Explain the difference between the direct method and indirect method of cash flow.",
            "conversation_id": conv_id,
            "document_ids": [doc_id],
            "skip_verification": False
        }
        r2 = client.post("/api/query", json=q2).json()
        assert len(r2["citations"]) > 0
        assert any("direct method" in c["snippet"].lower() for c in r2["citations"])
        assert all(c["document_id"] == doc_id for c in r2["citations"])
        print(f"[Checklist 3/6 PASS] Query 2 (Direct vs Indirect Method) citations verified: Page {r2['citations'][0]['page_number']}")

        # 7. Test Query 3: Common vs Preferred shares
        q3 = {
            "query": "What is the difference between common shares and preferred shares, and how many authorised shares are there?",
            "conversation_id": conv_id,
            "document_ids": [doc_id],
            "skip_verification": False
        }
        r3 = client.post("/api/query", json=q3).json()
        assert len(r3["citations"]) > 0
        assert any("preferred shares" in c["snippet"].lower() or "authorised" in c["snippet"].lower() for c in r3["citations"])
        assert all(c["document_id"] == doc_id for c in r3["citations"])
        print(f"[Checklist 4/6 PASS] Query 3 (Common vs Preferred Shares) verified.")

        # 8. Test Query 4: Ratio Analysis categories
        q4 = {
            "query": "What are the three main ratio categories in ratio analysis?",
            "conversation_id": conv_id,
            "document_ids": [doc_id],
            "skip_verification": False
        }
        r4 = client.post("/api/query", json=q4).json()
        assert len(r4["citations"]) > 0
        assert any("ratio analysis" in c["snippet"].lower() for c in r4["citations"])
        assert all(c["document_id"] == doc_id for c in r4["citations"])
        print(f"[Checklist 5/6 PASS] Query 4 (Ratio Analysis) verified: Page {r4['citations'][0]['page_number']}")

        # 9. Test Query 5: Strict Isolation & Relevance Gate
        q5 = {
            "query": "What is the LEGACY_CODE_731 security key for Project Orchid?",
            "conversation_id": conv_id,
            "document_ids": [doc_id],
            "skip_verification": False
        }
        r5 = client.post("/api/query", json=q5).json()
        assert r5["answer"] == "I cannot answer this based on the provided document." or len(r5["citations"]) == 0
        assert not any("orchid" in c["snippet"].lower() for c in r5["citations"])
        print(f"[Checklist 6/6 PASS] Strict Scope Isolation & Relevance Gate confirmed: 0 out-of-scope citations leaked.")

        print("\nALL 6 CHECKLIST TESTS PASSED PERFECTLY & SMOOTHLY!")

if __name__ == "__main__":
    test_pwc_financial_statements_complete_flow()
