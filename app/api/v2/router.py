import json
import uuid
import asyncio
from typing import List
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException, Request, Header
from fastapi.responses import JSONResponse, StreamingResponse
from app.config import settings
from app.schemas import DocumentResponse, QueryRequest, QueryResponse, ConversationResponse
from app.repository import get_repository
from app.rag import get_rag_service
from app.storage.s3_storage import get_s3_storage
from app.cache.semantic_cache import get_semantic_cache

v2_router = APIRouter(prefix="/v2", tags=["v2 (Enterprise Hybrid & Streaming)"])


@v2_router.post("/documents/upload", response_model=DocumentResponse, status_code=202)
async def upload_document_v2(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    x_tenant_id: str = Header("default_tenant")
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    doc_id = str(uuid.uuid4())
    s3_storage = get_s3_storage()
    saved_uri = s3_storage.upload_file(file.file, doc_id, file.filename, x_tenant_id)

    repo = get_repository()
    repo.create_document(
        doc_id=doc_id,
        filename=file.filename,
        file_type=file.content_type or "application/pdf",
        page_count=0,
        file_path=saved_uri,
        tenant_id=x_tenant_id
    )

    rag = get_rag_service()
    background_tasks.add_task(rag.ingest_document, saved_uri, doc_id, file.filename)

    return JSONResponse(
        status_code=202,
        content={
            "id": doc_id,
            "filename": file.filename,
            "status": "processing",
            "progress": 0.0,
            "created_at": "",
            "error": None
        }
    )


@v2_router.post("/query", response_model=QueryResponse)
def query_rag_v2(req: QueryRequest, x_tenant_id: str = Header("default_tenant")):
    # 1. Semantic Cache check
    cache = get_semantic_cache()
    cached_hit = cache.get(req.query)
    if cached_hit:
        return QueryResponse(
            answer=cached_hit["answer"],
            citations=[],
            verification=None,
            latency_ms=2.5,
            retrieval_latency_ms=0.5,
            conversation_id=req.conversation_id or "cached_conv"
        )

    rag = get_rag_service()
    res = rag.query(req)
    if "cannot answer" not in res.answer.lower():
        cache.set(req.query, res.answer)
    return res


@v2_router.post("/query/stream")
async def query_rag_stream_v2(req: QueryRequest, x_tenant_id: str = Header("default_tenant")):
    """Server-Sent Events (SSE) streaming query response for long narrative queries."""
    async def event_generator():
        rag = get_rag_service()
        res = rag.query(req)
        words = res.answer.split()
        for i in range(0, len(words), 3):
            chunk_str = " ".join(words[i:i+3]) + " "
            yield f"data: {json.dumps({'chunk': chunk_str})}\n\n"
            await asyncio.sleep(0.02)
        yield f"data: {json.dumps({'done': True, 'sources': [s.chunk_id for s in res.citations]})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

