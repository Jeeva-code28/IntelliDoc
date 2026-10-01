import io

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


client = TestClient(app)


def test_rejects_uploads_over_max_size():
    original_limit = settings.MAX_UPLOAD_BYTES
    settings.MAX_UPLOAD_BYTES = 100
    try:
        response = client.post(
            "/api/documents/upload",
            files={"file": ("big.txt", b"x" * 200, "text/plain")},
            data={"conversation_id": "conv-large-test"},
        )
        assert response.status_code == 413, response.text
    finally:
        settings.MAX_UPLOAD_BYTES = original_limit
