from abc import ABC, abstractmethod
from typing import List, Tuple, Optional, Dict, Any
import numpy as np
from app.schemas import Chunk, DocumentStatusResponse, ConversationResponse, MessageResponse


class BaseRepository(ABC):
    """Abstract base repository contract for single-node SQLite and multi-node PostgreSQL."""

    @abstractmethod
    def create_document(
        self,
        doc_id: str,
        filename: str,
        file_type: str,
        page_count: int,
        file_path: str,
        tenant_id: str = "default_tenant"
    ) -> None:
        pass

    @abstractmethod
    def update_document_status(
        self,
        doc_id: str,
        status: str,
        progress: float = 0.0,
        error: Optional[str] = None
    ) -> None:
        pass

    @abstractmethod
    def get_document(self, doc_id: str, tenant_id: str = "default_tenant") -> Optional[DocumentStatusResponse]:
        pass

    @abstractmethod
    def get_all_documents(self, tenant_id: str = "default_tenant") -> List[DocumentStatusResponse]:
        pass

    @abstractmethod
    def insert_chunks_and_vectors(
        self,
        chunks: List[Chunk],
        vectors: np.ndarray,
        tenant_id: str = "default_tenant"
    ) -> None:
        pass

    @abstractmethod
    def load_all_chunks(self, tenant_id: str = "default_tenant") -> List[Chunk]:
        pass

    @abstractmethod
    def load_all_vectors(self, tenant_id: str = "default_tenant") -> Tuple[List[str], np.ndarray]:
        pass

    @abstractmethod
    def check_integrity_gate(self, doc_id: str) -> bool:
        pass

    @abstractmethod
    def create_conversation(self, conversation_id: str, tenant_id: str = "default_tenant") -> None:
        pass

    @abstractmethod
    def add_message(
        self,
        message_id: str,
        conversation_id: str,
        role: str,
        content: str,
        sources: List[str] = []
    ) -> None:
        pass

    @abstractmethod
    def get_conversation(self, conversation_id: str) -> Optional[ConversationResponse]:
        pass
