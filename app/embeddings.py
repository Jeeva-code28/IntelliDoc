import numpy as np
from typing import List
from sentence_transformers import SentenceTransformer
from app.config import settings


class EmbeddingEngine:
    """
    Local BGE Embedding Engine (BAAI/bge-small-en-v1.5, 384 dimensions).
    Passages are embedded bare.
    Queries are prefixed with 'Represent this sentence for searching relevant passages: '.
    All vectors are normalized to L2 unit length (norm = 1.0).
    """

    def __init__(self, model_name: str = settings.EMBEDDING_MODEL_NAME):
        self.model_name = model_name
        self.dim = settings.EMBEDDING_DIM
        self.query_prefix = settings.QUERY_PREFIX
        # Initialize SentenceTransformer
        self.model = SentenceTransformer(model_name)

    def embed_passages(self, texts: List[str], batch_size: int = settings.EMBED_BATCH_SIZE) -> np.ndarray:
        """
        Embed bare text passages into (N, 384) float32 numpy matrix, L2 normalized.
        """
        if not texts:
            return np.empty((0, self.dim), dtype=np.float32)

        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        return embeddings.astype(np.float32)

    def embed_query(self, query: str) -> np.ndarray:
        """
        Embed query prefixed with instruction prefix into (384,) float32 numpy vector, L2 normalized.
        """
        prefixed_query = f"{self.query_prefix}{query.strip()}"
        embedding = self.model.encode(
            [prefixed_query],
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True
        )[0]
        return embedding.astype(np.float32)


# Global singleton instance
_embedding_engine = None


def get_embedding_engine() -> EmbeddingEngine:
    global _embedding_engine
    if _embedding_engine is None:
        _embedding_engine = EmbeddingEngine()
    return _embedding_engine
