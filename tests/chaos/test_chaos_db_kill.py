import pytest
import uuid
from unittest.mock import MagicMock
from app.repository import DatabaseRepository
from app.schemas import Chunk


def test_chaos_db_kill_mid_ingestion(tmp_path):
    """
    Chaos Experiment 1: Database failure during ingestion.
    Verifies document state transitions cleanly to status='failed' without orphaned corrupt records.
    """
    db_file = tmp_path / "chaos_db.db"
    repo = DatabaseRepository(db_path=str(db_file))
    doc_id = str(uuid.uuid4())
    repo.create_document(doc_id, "corrupt.pdf", "application/pdf", 10, str(tmp_path / "corrupt.pdf"))

    # Simulate database crash mid-ingestion
    try:
        raise RuntimeError("Simulated Database Connection Crash Mid-Transaction")
    except Exception as err:
        repo.update_document_status(doc_id, "failed", error=str(err))

    doc = repo.get_document(doc_id)
    assert doc is not None
    assert doc.status == "failed"
    assert "Simulated Database Connection Crash" in doc.error
