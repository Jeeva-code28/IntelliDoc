import logging
import numpy as np
from typing import List, Tuple, Optional, Dict, Any
from app.config import settings
from app.schemas import Chunk
from app.vector_store.base import VectorStore

logger = logging.getLogger("project_npn")


class QdrantVectorStore(VectorStore):
    """
    Production-grade Qdrant Vector Store Implementation.
    Supports HNSW index search (m=16, ef_construct=128), payload filtering by tenant_id,
    and automatic local memory fallback if external Qdrant server is unreachable.
    """

    def __init__(
        self,
        url: str = "http://localhost:6333",
        api_key: Optional[str] = None,
        collection_name: str = "npn_chunks",
        tenant_id: str = "default_tenant"
    ):
        self.url = url
        self.api_key = api_key
        self.collection_name = collection_name
        self.tenant_id = tenant_id
        self.dim = settings.EMBEDDING_DIM
        self.client = None
        self._fallback_storage: Dict[str, Tuple[str, str, np.ndarray]] = {}  # cid -> (tenant_id, doc_id, vector)
        self._init_client()

    def _init_client(self) -> None:
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import VectorParams, Distance, HnswConfigDiff

            # Attempt connection to Qdrant server or memory mode
            if self.url == ":memory:":
                self.client = QdrantClient(location=":memory:")
            else:
                self.client = QdrantClient(url=self.url, api_key=self.api_key, timeout=2.0)

            # Ensure collection exists
            collections = [c.name for c in self.client.get_collections().collections]
            if self.collection_name not in collections:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=self.dim, distance=Distance.COSINE),
                    hnsw_config=HnswConfigDiff(m=16, ef_construct=128)
                )
            logger.info(f"Initialized QdrantVectorStore on collection '{self.collection_name}' with HNSW (m=16, ef=128).")
        except Exception as e:
            logger.warning(f"Qdrant client connection unavailable ({e}). Operating in resilient In-Memory fallback mode.")
            self.client = None

    def upsert(self, chunks: List[Chunk], vectors: np.ndarray, tenant_id: Optional[str] = None) -> None:
        active_tenant = tenant_id or self.tenant_id
        if not chunks or len(chunks) == 0:
            return

        vecs = vectors.astype(np.float32)
        # Maintain in-memory fallback storage for instant network partition fallback
        for i, c in enumerate(chunks):
            self._fallback_storage[c.id] = (active_tenant, c.document_id, vecs[i])

        if self.client:
            try:
                from qdrant_client.models import PointStruct
                points = []
                for i, c in enumerate(chunks):
                    payload = {
                        "tenant_id": active_tenant,
                        "document_id": c.document_id,
                        "filename": c.filename,
                        "page_number": c.page_number,
                        "section": c.section,
                        "text": c.text[:500]
                    }
                    points.append(PointStruct(
                        id=c.id if isinstance(c.id, int) else hash(c.id) & 0x7FFFFFFFFFFFFFFF,
                        vector=vecs[i].tolist(),
                        payload=payload
                    ))
                self.client.upsert(collection_name=self.collection_name, points=points)
            except Exception as e:
                logger.error(f"Qdrant upsert failed: {e}. Maintained in fallback storage.")

    def search(
        self,
        query_vec: np.ndarray,
        k: int = settings.TOP_K_DENSE,
        top_k: Optional[int] = None,
        tenant_id: Optional[str] = None
    ) -> List[Tuple[str, float]]:
        limit = top_k if top_k is not None else k
        active_tenant = tenant_id or self.tenant_id

        if self.client:
            try:
                from qdrant_client.models import Filter, FieldCondition, MatchValue
                search_result = self.client.search(
                    collection_name=self.collection_name,
                    query_vector=query_vec.tolist(),
                    query_filter=Filter(
                        must=[FieldCondition(key="tenant_id", match=MatchValue(value=active_tenant))]
                    ),
                    limit=limit
                )
                return [(str(hit.id), float(hit.score)) for hit in search_result]
            except Exception as e:
                logger.warning(f"Qdrant search error: {e}. Falling back to exact vector search.")

        # Fallback in-memory search
        tenant_items = [(cid, val[2]) for cid, val in self._fallback_storage.items() if val[0] == active_tenant]
        if not tenant_items:
            return []

        cids = [item[0] for item in tenant_items]
        matrix = np.vstack([item[1] for item in tenant_items])
        scores = np.dot(matrix, query_vec)

        top_limit = min(limit, len(cids))
        partitioned = np.argpartition(scores, -top_limit)[-top_limit:]
        sorted_idx = partitioned[np.argsort(scores[partitioned])[::-1]]

        return [(cids[idx], float(scores[idx])) for idx in sorted_idx]

    def delete(self, document_id: str) -> None:
        if self.client:
            try:
                from qdrant_client.models import Filter, FieldCondition, MatchValue
                self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=Filter(
                        must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
                    )
                )
            except Exception as e:
                logger.error(f"Qdrant delete failed: {e}")

        to_del = [cid for cid, val in self._fallback_storage.items() if val[1] == document_id]
        for cid in to_del:
            del self._fallback_storage[cid]

    def clear(self) -> None:
        if self.client:
            try:
                self.client.delete_collection(collection_name=self.collection_name)
            except Exception:
                pass
        self._fallback_storage.clear()
