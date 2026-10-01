from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple, Literal
from pydantic import BaseModel, Field
from datetime import datetime


@dataclass(frozen=True)
class Chunk:
    """
    Central Data Model for Project NPN. Immutable and thread-safe.
    Dual-text design:
      - text: For embedding + BM25 (findability/linearized)
      - context_text: For LLM context (readability/markdown/full grid)
    """
    id: str
    document_id: str
    filename: str
    page_number: int
    section: Optional[str]
    content_type: str  # "text" | "table" | "figure" | "image" | "video" | "audio" | "attachment"
    
    text: str
    context_text: str
    
    conversation_id: Optional[str] = None
    bbox: Optional[Tuple[float, float, float, float]] = None
    asset_path: Optional[str] = None
    temporal_start: Optional[float] = None
    temporal_end: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# API Request/Response Schemas

class DocumentResponse(BaseModel):
    id: str
    filename: str
    file_type: str = "document"
    page_count: int = 1
    status: str
    progress: float = 0.0
    conversation_id: Optional[str] = None
    created_at: str = ""
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    status: str
    message: str
    conversation_id: Optional[str] = None


class QueryRequest(BaseModel):
    query: str
    conversation_id: Optional[str] = None
    llm_provider: Optional[str] = None


class CitationSource(BaseModel):
    chunk_id: str
    filename: str
    page_number: int
    section: Optional[str] = None
    content_type: str
    snippet: str
    score: float
    bbox: Optional[Tuple[float, float, float, float]] = None
    asset_path: Optional[str] = None
    temporal_start: Optional[float] = None
    temporal_end: Optional[float] = None


class VerificationBadge(BaseModel):
    status: Literal["supported", "partial", "unsupported"]
    reasoning: str
    supported_claims: List[str] = []
    unsupported_claims: List[str] = []


class QueryResponse(BaseModel):
    answer: str
    citations: List[CitationSource] = []
    verification: Optional[VerificationBadge] = None
    latency_ms: float
    retrieval_latency_ms: float
    conversation_id: str


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    sources: List[str] = []
    created_at: str = ""


class ConversationResponse(BaseModel):
    id: str
    created_at: str = ""
    title: Optional[str] = None
    messages: List[MessageResponse] = []
    documents: List[DocumentResponse] = []


class ConversationItemResponse(BaseModel):
    id: str
    title: str
    created_at: str = ""
    document_count: int = 0
    message_count: int = 0


class HistoryArchiveItem(BaseModel):
    id: str
    conversation_id: str
    title: str
    created_at: str = ""
    deleted_at: str = ""
    message_count: int = 0
    document_count: int = 0
    transcript_summary: str = ""


class HistoryArchiveDetail(BaseModel):
    id: str
    conversation_id: str
    title: str
    created_at: str = ""
    deleted_at: str = ""
    message_count: int = 0
    document_count: int = 0
    transcript_summary: str = ""
    markdown_content: Optional[str] = None
    json_data: Optional[Dict[str, Any]] = None


# Aliases for backward compatibility
DocumentStatusResponse = DocumentResponse
RAGResponse = QueryResponse
Citation = CitationSource
MessageSchema = MessageResponse
ConversationSchema = ConversationResponse


