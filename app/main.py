import os
import uuid
import shutil
from pathlib import Path
from typing import List

from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException, Depends, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.schemas import DocumentResponse, QueryRequest, QueryResponse, ConversationResponse
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
async def upload_document(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    allowed_exts = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".mp4", ".mov", ".avi", ".mp3", ".wav", ".csv", ".zip"}
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed_exts:
        raise HTTPException(status_code=400, detail=f"Unsupported file format '{ext}'. Allowed: {', '.join(sorted(allowed_exts))}")

    doc_id = str(uuid.uuid4())
    saved_path = settings.UPLOADS_DIR / f"{doc_id}_{file.filename}"
    saved_path.parent.mkdir(parents=True, exist_ok=True)

    with open(saved_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    repo = get_repository()
    repo.create_document(
        doc_id=doc_id,
        filename=file.filename,
        file_type=file.content_type or f"application/{ext.replace('.', '')}",
        page_count=1 if ext != ".pdf" else 0,
        file_path=str(saved_path)
    )

    rag = get_rag_service()
    background_tasks.add_task(rag.ingest_document, str(saved_path), doc_id, file.filename)

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


@app.get("/api/documents", response_model=List[DocumentResponse])
def list_documents():
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
        created_at=d.created_at or "",
        error=d.error
    )


@app.post("/api/query", response_model=QueryResponse)
def query_rag(req: QueryRequest):
    rag = get_rag_service()
    return rag.query(req)


@app.get("/api/conversations/{conv_id}", response_model=ConversationResponse)
def get_conversation(conv_id: str):
    repo = get_repository()
    conv = repo.get_conversation(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return conv
