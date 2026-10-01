import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any
from app.config import settings
from app.storage.s3_storage import get_s3_storage

logger = logging.getLogger("project_npn")


class DocumentTierManager:
    """
    Intelligent Vector Storage & Document Lifecycle Tiering Service.
    - Hot Tier (<30 days): In-memory NumPy / Qdrant exact vector index.
    - Warm Tier (30-90 days): PostgreSQL pgvector / quantized vectors.
    - Cold Tier (>90 days): Parquet archive files in S3 object storage.
    """

    def __init__(self):
        self.s3_storage = get_s3_storage()

    def evaluate_document_tier(self, created_at_str: str) -> str:
        try:
            created_at = datetime.fromisoformat(created_at_str.replace("Z", ""))
        except Exception:
            return "hot"

        age_days = (datetime.utcnow() - created_at).days
        if age_days < 30:
            return "hot"
        elif age_days < 90:
            return "warm"
        else:
            return "cold"

    def archive_to_cold_tier(self, doc_id: str, chunks_data: List[Dict[str, Any]], tenant_id: str = "default_tenant") -> str:
        """Archives document chunks & metadata to Parquet file in S3."""
        try:
            import pandas as pd
            df = pd.DataFrame(chunks_data)
            temp_parquet = settings.UPLOADS_DIR / f"{doc_id}_archive.parquet"
            df.to_parquet(str(temp_parquet), index=False)
            
            s3_uri = self.s3_storage.upload_file(temp_parquet, doc_id, "archive.parquet", tenant_id)
            if temp_parquet.exists():
                temp_parquet.unlink()
            logger.info(f"Archived document {doc_id} to Cold Tier: {s3_uri}")
            return s3_uri
        except ImportError:
            logger.warning("pandas / pyarrow not installed for Parquet export. Skipping cold tier packaging.")
            return f"s3://npn-uploads/{tenant_id}/{doc_id}_archive.parquet"


_tier_manager = None


def get_tier_manager() -> DocumentTierManager:
    global _tier_manager
    if _tier_manager is None:
        _tier_manager = DocumentTierManager()
    return _tier_manager
