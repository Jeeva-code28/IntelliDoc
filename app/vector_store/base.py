from abc import ABC, abstractmethod
from typing import List, Tuple
import numpy as np
from app.schemas import Chunk


class VectorStore(ABC):
    """
    Abstract Base Class for Project NPN Vector Store.
    Defines scaling interface allowing single-node exact NumPy store
    or distributed vector engines (e.g. Qdrant HNSW) to be swapped cleanly.
    """

    @abstractmethod
    def upsert(self, chunks: List[Chunk], vectors: np.ndarray) -> None:
        """Insert or update chunks and their float32 embedding vectors."""
        pass

    @abstractmethod
    def search(self, query_vec: np.ndarray, k: int) -> List[Tuple[str, float]]:
        """Search top-k most similar chunks given an L2 normalized query vector."""
        pass

    @abstractmethod
    def delete(self, document_id: str) -> None:
        """Delete all vectors associated with a document_id."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all stored vectors and indices."""
        pass
