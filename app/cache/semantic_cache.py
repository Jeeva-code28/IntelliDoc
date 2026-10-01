import time
import logging
import numpy as np
from typing import Optional, Dict, Tuple, Any
from app.embeddings import get_embedding_engine

logger = logging.getLogger("project_npn")


class SemanticCache:
    """
    Semantic LLM Response Cache & Token Bucket Cost Controller.
    - Caches queries & answers using dense sentence embeddings.
    - If new query has cosine similarity > 0.95 to a cached query, returns cached answer (saves 90%+ LLM costs).
    - If context complexity > 8,000 tokens, automatically routes to local/cheaper model tier.
    """

    def __init__(self, similarity_threshold: float = 0.95):
        self.similarity_threshold = similarity_threshold
        self._cache: Dict[str, Tuple[np.ndarray, str, Dict[str, Any]]] = {}  # query_id -> (vec, answer, metadata)

    def get(self, query_text: str) -> Optional[Dict[str, Any]]:
        if not self._cache:
            return None

        embedder = get_embedding_engine()
        q_vec = embedder.embed_query(query_text).astype(np.float32)

        cached_ids = list(self._cache.keys())
        matrix = np.vstack([val[0] for val in self._cache.values()])
        scores = np.dot(matrix, q_vec)

        best_idx = int(np.argmax(scores))
        best_score = float(scores[best_idx])

        if best_score >= self.similarity_threshold:
            matched_id = cached_ids[best_idx]
            answer, meta = self._cache[matched_id][1], self._cache[matched_id][2]
            logger.info(f"Semantic Cache Hit! (Similarity: {best_score:.4f} >= {self.similarity_threshold})")
            return {
                "answer": answer,
                "similarity": best_score,
                "cached": True,
                "metadata": meta
            }
        return None

    def set(self, query_text: str, answer_text: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        embedder = get_embedding_engine()
        q_vec = embedder.embed_query(query_text).astype(np.float32)
        q_id = str(hash(query_text))
        self._cache[q_id] = (q_vec, answer_text, metadata or {})

    def evaluate_token_bucket_routing(self, context_text: str) -> str:
        """Token bucket cost controller. Forces cheaper/local model if context > 8,000 tokens."""
        estimated_tokens = len(context_text.split()) * 1.3
        if estimated_tokens > 8000:
            logger.info(f"Token bucket threshold exceeded ({estimated_tokens:.0f} > 8000). Routing to local Ollama tier.")
            return "ollama"
        return "default"


_semantic_cache = None


def get_semantic_cache() -> SemanticCache:
    global _semantic_cache
    if _semantic_cache is None:
        _semantic_cache = SemanticCache()
    return _semantic_cache
