import os
import uuid
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException, Depends, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.schemas import (
    DocumentResponse, 
    DocumentUploadResponse, 
    QueryRequest, 
    QueryResponse, 
    ConversationResponse,
    ConversationItemResponse,
    HistoryArchiveItem,
    HistoryArchiveDetail
)
from app.repository import get_repository
from app.rag import get_rag_service
from app.resilience.circuit_breaker import get_circuit_breaker
from app.observability.logging import get_prometheus_metrics

from app.api.v1.router import v1_router
from app.api.v2.router import v2_router
from app.middleware.rate_limiter import RateLimitMiddleware


app = FastAPI(
    title="Project NPN (Narrative, Proof, Numbers)",
    description="High-performance, local-first multimodal RAG for financial and technical intelligence across PDF, Video, Audio, Images, and Data.",
    version="2.0.0"
)

app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router)
app.include_router(v2_router)

# Create static directory if missing
static_dir = Path("static")
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Mount assets directory for previews
assets_dir = settings.ASSETS_DIR
assets_dir.mkdir(parents=True, exist_ok=True)
app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")


@app.on_event("startup")
def startup_event():
    rag = get_rag_service()
    rag.initialize_indexes()


@app.get("/", response_class=HTMLResponse)
def read_root():
    index_file = static_dir / "index.html"
    if index_file.exists():
        return index_file.read_text(encoding="utf-8")
    return "<h1>Project NPN Active</h1>"


@app.get("/health")
def health_check():
    """Health check endpoint reporting provider circuit breaker states."""
    cb = get_circuit_breaker()
    return {
        "status": "healthy",
        "circuit_breaker": cb.get_status(),
        "vector_store": "NumpyVectorStore (Exact Search)",
        "multimodal_engines": ["PyMuPDF", "VideoKeyframes", "AudioTranscripts", "ImageVision", "TabularCSV"]
    }


@app.get("/metrics")
def prometheus_metrics():
    """Prometheus metrics endpoint."""
    data, content_type = get_prometheus_metrics()
    return Response(content=data, media_type=content_type)


@app.post("/api/documents/upload", response_model=DocumentResponse, status_code=202)
async def upload_document(
    background_tasks: BackgroundTasks, 
    file: UploadFile = File(...),
    conversation_id: Optional[str] = Form(None)
):
    allowed_exts = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".mp4", ".mov", ".avi", ".mp3", ".wav", ".csv", ".tsv", ".zip", ".txt", ".md", ".markdown", ".log", ".json"}
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed_exts:
        raise HTTPException(status_code=400, detail=f"Unsupported file format '{ext}'. Allowed: {', '.join(sorted(allowed_exts))}")

    target_conv_id = conversation_id or "default_conv"
    doc_id = str(uuid.uuid4())
    saved_path = settings.UPLOADS_DIR / f"{doc_id}_{file.filename}"
    saved_path.parent.mkdir(parents=True, exist_ok=True)

    with open(saved_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    repo = get_repository()
    repo.ensure_conversation(target_conv_id, title=f"Chat - {file.filename[:25]}")
    repo.create_document(
        doc_id=doc_id,
        filename=file.filename,
        file_type=file.content_type or f"application/{ext.replace('.', '')}",
        page_count=1 if ext != ".pdf" else 0,
        file_path=str(saved_path),
        conversation_id=target_conv_id
    )

    rag = get_rag_service()
    background_tasks.add_task(rag.ingest_document, str(saved_path), doc_id, file.filename, target_conv_id)

    return JSONResponse(
        status_code=202,
        content={
            "id": doc_id,
            "filename": file.filename,
            "status": "processing",
            "progress": 0.0,
            "conversation_id": target_conv_id,
            "created_at": "",
            "error": None
        }
    )


@app.get("/api/documents", response_model=List[DocumentResponse])
def list_documents(conversation_id: Optional[str] = None):
    repo = get_repository()
    docs = repo.get_all_documents(conversation_id=conversation_id)
    return [
        DocumentResponse(
            id=d.id,
            filename=d.filename,
            status=d.status,
            progress=d.progress,
            conversation_id=d.conversation_id,
            created_at=d.created_at or "",
            error=d.error
        ) for d in docs
    ]


@app.get("/api/documents/{doc_id}", response_model=DocumentResponse)
def get_document_status(doc_id: str):
    repo = get_repository()
    d = repo.get_document(doc_id)
    if not d:
        raise HTTPException(status_code=404, detail="Document not found.")
    return DocumentResponse(
        id=d.id,
        filename=d.filename,
        status=d.status,
        progress=d.progress,
        conversation_id=d.conversation_id,
        created_at=d.created_at or "",
        error=d.error
    )


@app.post("/api/query", response_model=QueryResponse)
def query_rag(req: QueryRequest):
    rag = get_rag_service()
    return rag.query(req)


@app.get("/api/conversations", response_model=List[ConversationItemResponse])
def list_conversations():
    repo = get_repository()
    convs = repo.list_conversations()
    return [
        ConversationItemResponse(
            id=c["id"],
            title=c["title"],
            created_at=c["created_at"] or "",
            document_count=c["document_count"],
            message_count=c["message_count"]
        ) for c in convs
    ]


@app.post("/api/conversations", response_model=ConversationItemResponse)
def create_conversation(title: Optional[str] = None):
    repo = get_repository()
    conv_id = str(uuid.uuid4())
    clean_title = title or "New Conversation"
    repo.create_conversation(conv_id, clean_title)
    return ConversationItemResponse(
        id=conv_id,
        title=clean_title,
        created_at="",
        document_count=0,
        message_count=0
    )


@app.get("/api/conversations/{conv_id}", response_model=ConversationResponse)
def get_conversation(conv_id: str):
    repo = get_repository()
    conv = repo.get_conversation(conv_id)
    if not conv:
        # Create empty conversation on the fly
        repo.create_conversation(conv_id, "New Conversation")
        conv = repo.get_conversation(conv_id)
    return conv


@app.get("/api/conversations/{conv_id}/documents", response_model=List[DocumentResponse])
def get_conversation_documents(conv_id: str):
    repo = get_repository()
    docs = repo.get_all_documents(conversation_id=conv_id)
    return [
        DocumentResponse(
            id=d.id,
            filename=d.filename,
            status=d.status,
            progress=d.progress,
            conversation_id=d.conversation_id,
            created_at=d.created_at or "",
            error=d.error
        ) for d in docs
    ]


@app.delete("/api/conversations/{conv_id}")
def delete_conversation(conv_id: str):
    """
    Deletes a conversation, purging active records & memory partitions.
    Compiles and exports all prompts, replies, and citations to a history archive file.
    """
    rag = get_rag_service()
    archive_meta = rag.delete_conversation(conv_id)
    if not archive_meta:
        # Fallback if conversation had no record or was empty
        repo = get_repository()
        repo.delete_conversation(conv_id)
        return {
            "success": True,
            "message": f"Conversation {conv_id} deleted.",
            "archive": None
        }

    return {
        "success": True,
        "message": f"Conversation {conv_id} deleted and archived to History.",
        "archive": archive_meta
    }


# ==========================================
# History Archives API
# ==========================================

@app.get("/api/history", response_model=List[HistoryArchiveItem])
def list_history_archives():
    """Returns list of all archived deleted conversations."""
    repo = get_repository()
    records = repo.list_history_archives()
    return [
        HistoryArchiveItem(
            id=r["id"],
            conversation_id=r["conversation_id"] or "",
            title=r["title"] or "Archived Conversation",
            created_at=r["created_at"] or "",
            deleted_at=r["deleted_at"] or "",
            message_count=r["message_count"] or 0,
            document_count=r["document_count"] or 0,
            transcript_summary=r.get("transcript_summary", "")
        )
        for r in records
    ]


@app.get("/api/history/{history_id}", response_model=HistoryArchiveDetail)
def get_history_archive_detail(history_id: str):
    """Returns full archived transcript, citations, and export data."""
    repo = get_repository()
    record = repo.get_history_archive(history_id)
    if not record:
        raise HTTPException(status_code=404, detail="History archive not found.")

    md_content = ""
    json_data = None

    if record.get("md_file_path") and Path(record["md_file_path"]).exists():
        try:
            md_content = Path(record["md_file_path"]).read_text(encoding="utf-8")
        except Exception:
            pass

    if record.get("json_file_path") and Path(record["json_file_path"]).exists():
        try:
            raw_json = Path(record["json_file_path"]).read_text(encoding="utf-8")
            import json
            json_data = json.loads(raw_json)
        except Exception:
            pass

    return HistoryArchiveDetail(
        id=record["id"],
        conversation_id=record["conversation_id"] or "",
        title=record["title"] or "Archived Conversation",
        created_at=record["created_at"] or "",
        deleted_at=record["deleted_at"] or "",
        message_count=record["message_count"] or 0,
        document_count=record["document_count"] or 0,
        transcript_summary=record.get("transcript_summary", ""),
        markdown_content=md_content,
        json_data=json_data
    )


@app.get("/api/history/{history_id}/download")
def download_history_archive(history_id: str, format: str = "md"):
    """Downloads the generated history archive file (.md or .json)."""
    repo = get_repository()
    record = repo.get_history_archive(history_id)
    if not record:
        raise HTTPException(status_code=404, detail="History archive not found.")

    fmt = format.lower().strip()
    if fmt == "json":
        file_path = record.get("json_file_path")
        media_type = "application/json"
        ext = "json"
    else:
        file_path = record.get("md_file_path")
        media_type = "text/markdown"
        ext = "md"

    if not file_path or not Path(file_path).exists():
        raise HTTPException(status_code=404, detail=f"Archive file ({fmt}) not found on disk.")

    clean_filename = f"{history_id[:8]}_{record['title'].replace(' ', '_')[:25]}.{ext}"
    return FileResponse(
        path=file_path,
        filename=clean_filename,
        media_type=media_type
    )


@app.delete("/api/history/{history_id}")
def delete_history_archive(history_id: str):
    """Permanently deletes a single history archive file."""
    repo = get_repository()
    deleted = repo.delete_history_archive(history_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="History archive not found.")
    return {"success": True, "message": f"History archive {history_id} deleted."}


@app.delete("/api/history")
def clear_all_history():
    """Clears all history archives and their files."""
    repo = get_repository()
    repo.clear_all_history_archives()
    return {"success": True, "message": "All history archives cleared."}


