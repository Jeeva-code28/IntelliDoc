import io
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


class IngestionStormUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def upload_94p_pdf(self):
        files = {
            "file": ("load_test_94p.pdf", PDF_PAYLOAD, "application/pdf")
        }
        headers = {
            "X-Tenant-ID": "tenant_load_test",
            "X-Tenant-Tier": "enterprise"
        }
        with self.client.post("/api/documents/upload", files=files, headers=headers, catch_response=True) as resp:
            if resp.status_code == 202:
                resp.success()
            else:
                resp.failure(f"Expected 202 status code, got {resp.status_code}")
