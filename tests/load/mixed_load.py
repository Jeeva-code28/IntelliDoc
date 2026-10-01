import fitz
from locust import HttpUser, task, between


def create_mock_94p_pdf() -> bytes:
    doc = fitz.open()
    for p in range(94):
        page = doc.new_page()
        page.insert_text((50, 50), f"Financial Section Page {p+1}", fontsize=14)
        page.insert_text((50, 80), f"Revenue for Q{p%4+1} was {1000 + p*10} Lakhs.", fontsize=10)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


PDF_PAYLOAD = create_mock_94p_pdf()


class MixedLoadUser(HttpUser):
    wait_time = between(0.1, 0.5)

    @task(5)
    def query_rag(self):
        payload = {
            "query": "What is the revenue for FY2025?",
            "conversation_id": "mixed_load_conv"
        }
        headers = {
            "Content-Type": "application/json",
            "X-Tenant-ID": "tenant_mixed",
            "X-Tenant-Tier": "enterprise"
        }
        self.client.post("/api/query", json=payload, headers=headers)

    @task(1)
    def upload_document(self):
        files = {
            "file": ("mixed_load.pdf", PDF_PAYLOAD, "application/pdf")
        }
        headers = {
            "X-Tenant-ID": "tenant_mixed",
            "X-Tenant-Tier": "enterprise"
        }
        self.client.post("/api/documents/upload", files=files, headers=headers)
