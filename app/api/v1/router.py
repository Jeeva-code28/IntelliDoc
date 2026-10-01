import uuid
import shutil
from typing import List
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException, Response, Request
from fastapi.responses import JSONResponse
from app.config import settings
from app.schemas import DocumentResponse, QueryRequest, QueryResponse, ConversationResponse
from app.repository import get_repository
from app.rag import get_rag_service

v1_router = APIRouter(prefix="/v1", tags=["v1 (Legacy Exact Search)"])


@v1_router.get("/documents", response_model=List[DocumentResponse])
def list_documents_v1(response: Response):
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = "2027-01-01"
    repo = get_repository()
    docs = repo.get_all_documents()
    return [
        DocumentResponse(
            id=d.id,
            filename=d.filename,
            status=d.status,
            progress=d.progress,
            created_at=d.created_at or "",
            error=d.error
        ) for d in docs
    ]


@v1_router.post("/query", response_model=QueryResponse)
def query_rag_v1(req: QueryRequest, response: Response):
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = "2027-01-01"
    rag = get_rag_service()
    return rag.query(req)
