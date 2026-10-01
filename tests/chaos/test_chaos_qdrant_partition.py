import numpy as np
import pytest
from unittest.mock import MagicMock
from app.vector_store.qdrant_store import QdrantVectorStore
from app.schemas import Chunk


def test_chaos_qdrant_network_partition():
    """
    Chaos Experiment 2: Network partition to Qdrant cluster.
    Verifies transparent fallback to exact vector search without crashing RAG pipeline.
    """
    store = QdrantVectorStore(url="http://unreachable-qdrant-host:6333")
    
    # Simulate network partition by forcing client to None or raising Exception
    store.client = MagicMock()
    store.client.search.side_effect = ConnectionError("Qdrant cluster unreachable due to network partition.")

    chunks = [
        Chunk("c1", "doc1", "test.pdf", 1, "Sec", "text", "Revenue grew 25%", "Context")
    ]
    vecs = np.ones((1, 384), dtype=np.float32)
    store.upsert(chunks, vecs, tenant_id="tenant_chaos")

    # Perform search during network partition
    query_vec = vecs[0]
    results = store.search(query_vec, top_k=1, tenant_id="tenant_chaos")

    assert len(results) == 1
    assert results[0][0] == "c1"
