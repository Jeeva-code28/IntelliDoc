# Project: Project NPN Local-First Multimodal RAG Enhancement

## Architecture
- **Layer 1: Data Ingestion & Multimodal Parsing (`app/parsing.py`, `app/multimedia.py`)**
  - PyMuPDF text/table/figure parsing, font profiling, triage table filter, table triple-representation (markdown, linearized, structured+bbox).
  - Multimodal attachment extractor for video (temporal scenes/keyframes), audio (temporal transcript windows), images (vision captioning), and embedded documents.
  - Dual-text representation: `text` (linearized for search) and `context_text` (markdown/rich format for LLM).
- **Layer 2: Storage & Persistence (`app/repository.py`, `app/vector_store/`)**
  - SQLite database in WAL mode (`data/npn.db`), storing documents, chunks, conversations, messages.
  - Raw `float32` BLOB storage for 384-dim embeddings (40× smaller than JSON).
  - In-memory `NumpyVectorStore` and `BM25Index` loaded at startup and updated incrementally.
- **Layer 3: Cross-Modal Hybrid Retrieval & Gating (`app/retrieval.py`, `app/embeddings.py`)**
  - Dense asymmetric vector search (`bge-small-en-v1.5` 384-dim, query prefix on queries only).
  - Custom sparse BM25 index with pre-computed IDF scores (k1=1.5, b=0.75).
  - Reciprocal Rank Fusion (RRF with k=60).
  - Intent boosting (numeric → tables, visual → figures/images/videos, audio → audio transcripts).
  - Relevance Gate: dual threshold (dense >= 0.30 OR term coverage >= 0.60).
- **Layer 4: Grounded Multimodal Generation & Claim Verification (`app/llm.py`, `app/rag.py`)**
  - Multi-provider LLM client (Gemini 2.0 Flash primary, Groq, OpenAI, Ollama fallbacks).
  - Temperature = 0 for grounded synthesis with citation syntax `[S1]`, `[S2]`.
  - Claim verification engine scoring claims as `supported`, `partial`, or `unsupported`.
- **Layer 5: API Layer (`app/main.py`, `app/api/`)**
  - FastAPI endpoints: `/api/documents/upload`, `/api/documents/{id}`, `/api/documents`, `/api/query`, `/api/documents/{id}/page/{n}`, `/health`, `/metrics`.
- **Layer 6: Interactive Web Interface (`static/index.html`, `static/app.js`, `static/styles.css`)**
  - Drag-and-drop PDF upload with progress bar.
  - Chat workspace with latency badges, verification indicators, and interactive citation modal drawer supporting text, tables, images, video timestamps, and audio waveforms/windows.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Font Profiling & Heading Detection | Sample first 15 pages, modal body font size, detect headings for chunk boundaries | M1 | ARCHITECTURE §3 |
| 2 | Table Triage Filter | Page triage filter based on char count, digit ratio, and drawing rules (<8ms/page) | M1 | ARCHITECTURE §3.1 |
| 3 | Table Triple-Representation | Markdown grid for LLM context, linearized row sentences for search, structured cell + bbox | M1 | ARCHITECTURE §3.2 |
| 4 | Dual-Text Chunk Abstraction | Central `Chunk` dataclass with distinct `text` (embedding/BM25) and `context_text` (LLM context) | M1 | ARCHITECTURE §2.3 |
| 5 | Video Attachment Processing | Extract temporal keyframes, scene descriptions, and timestamp ranges (e.g. 00:00-00:15) | M1 | ORIGINAL_REQUEST R1 |
| 6 | Audio Attachment Processing | Extract 30s temporal transcript windows with timestamp ranges and format metadata | M1 | ORIGINAL_REQUEST R1 |
| 7 | Image & Figure Captioning | Extract raster figures/images, crop to PNG assets, generate vision captions with section context | M1 | ARCHITECTURE §3, R1 |
| 8 | Bounding Box Coordinate Extraction | Extract exact 4-element tuple (x0, y0, x1, y1) for citations and highlights | M1 | ARCHITECTURE §2.3, R1 |
| 9 | SQLite float32 BLOB Vector Storage | Store vectors as raw float32 BLOBs (40x smaller, sub-100ms retrieval) | M2 | ARCHITECTURE §2.4 |
| 10 | Exact Dense Vector Search | In-memory NumPy matrix multiplication with L2 normalized vectors and query prefix | M2 | ARCHITECTURE §4 |
| 11 | In-Memory BM25 Sparse Index | Custom BM25 index with pre-computed IDF scores at build time (k1=1.5, b=0.75) | M2 | ARCHITECTURE §4, §1.1 |
| 12 | Reciprocal Rank Fusion (RRF) | Rank-based fusion score = Σ 1 / (60 + rank) combining dense and sparse results | M2 | ARCHITECTURE §4.2 |
| 13 | Cross-Modal Intent Boosting | Query keyword classification boosting tables on numeric queries, figures/video on visual queries | M2 | ARCHITECTURE §4, R2 |
| 14 | Dual Relevance Gating | Refuse answering if best dense < 0.30 AND query term coverage < 0.60 | M2 | ARCHITECTURE §4.3 |
| 15 | Document Ingestion Pipeline | End-to-end 7-stage ingestion: Accept -> Font Profile -> Parse -> Heading Carry -> Embed -> Persist -> Integrity Gate | M3 | ARCHITECTURE §3 |
| 16 | Integrity Gate Verification | Assert chunk_count == vector_count before marking document status ready | M3 | ARCHITECTURE §3, §5.1 |
| 17 | Grounded Multi-Source Generation | Temperature=0 LLM prompt generating answer strictly grounded in [S1], [S2] citations | M3 | ARCHITECTURE §4, R3 |
| 18 | Claim Verification Engine | Secondary verification prompt classifying claims into supported, partial, unsupported | M3 | ARCHITECTURE §4, R3 |
| 19 | REST API Endpoints | /api/documents/upload, /api/documents/{id}, /api/documents, /api/query, /health, /metrics | M3 | ORIGINAL_REQUEST R3 |
| 20 | Web Upload Dropzone & Progress | Drag-and-drop PDF dropzone, upload card, real-time progress polling bar | M4 | ORIGINAL_REQUEST R4 |
| 21 | Interactive Chat Interface | Messages feed, LLM provider selection, sub-100ms latency badge, total latency badge | M4 | ORIGINAL_REQUEST R4 |
| 22 | Citation Drawer & Modal Preview | Clickable citation chips opening modal with content type, bbox highlight, snippet, asset preview | M4 | ORIGINAL_REQUEST R4 |
| 23 | Multimodal Media Cards & Timestamps | Dedicated UI cards for video/audio temporal windows and image figures with DOM sanitization | M4 | ORIGINAL_REQUEST R4 |
| 24 | E2E Test Suite & Adversarial Hardening | 100% pass across Unit, Integration, Multimodal, Security tests, and Tier 1-5 test suite | M5 | ORIGINAL_REQUEST R5 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Multimodal PDF & Attachment Extraction Engine | `app/parsing.py`, `app/multimedia.py`, `app/schemas.py` | none | PLANNED |
| M2 | Cross-Modal Hybrid Retrieval & Relevance Gating | `app/retrieval.py`, `app/vector_store/`, `app/embeddings.py` | M1 | PLANNED |
| M3 | Grounded Generation, Claim Verification & API | `app/rag.py`, `app/llm.py`, `app/main.py`, `app/repository.py` | M1, M2 | PLANNED |
| M4 | Interactive Multimodal Web Interface | `static/index.html`, `static/app.js`, `static/styles.css` | M3 | PLANNED |
| M5 | E2E Test Suite Pass & Adversarial Hardening | Full test execution, regression verification, edge case hardening | M1-M4, E2E Track | PLANNED |

## Interface Contracts
### Chunk Data Model (`app/schemas.py`)
```python
@dataclass(frozen=True)
class Chunk:
    id: str
    document_id: str
    filename: str
    page_number: int
    section: Optional[str]
    content_type: str  # "text" | "table" | "figure" | "image" | "video" | "audio" | "attachment"
    text: str          # For embedding & BM25 (linearized/searchable)
    context_text: str  # For LLM context (markdown grid/prose)
    bbox: Optional[Tuple[float, float, float, float]] = None
    asset_path: Optional[str] = None
    temporal_start: Optional[float] = None
    temporal_end: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### Retrieval Interface (`app/retrieval.py` ↔ `app/rag.py`)
- `VectorIndex.search(query_vec: np.ndarray, top_k: int) -> List[Tuple[str, float]]`
- `BM25Index.search(query: str, top_k: int) -> List[Tuple[str, float]]`
- `rrf_fusion(dense: List[Tuple[str, float]], sparse: List[Tuple[str, float]], k: int = 60) -> List[Tuple[str, float]]`
- `apply_intent_boost(query: str, rrf_results: List[Tuple[str, float]], chunk_map: Dict[str, Chunk]) -> List[Tuple[str, float]]`
- `calculate_term_coverage(query: str, chunk_text: str) -> float`

### API Contracts (`app/main.py`)
- `POST /api/documents/upload` -> `DocumentResponse` (status_code 202)
- `GET /api/documents/{id}` -> `DocumentResponse` (progress float, status)
- `POST /api/query` -> `QueryResponse` (answer, citations, verification, latencies)
- `GET /health` -> `{"status": "healthy", ...}`

## Code Layout
- `app/config.py`: Application settings and environment variables
- `app/schemas.py`: Pydantic models and Chunk dataclass
- `app/parsing.py`: PDF parsing, font profiling, table triage & extraction
- `app/multimedia.py`: Video, audio, image processing & captioning
- `app/embeddings.py`: SentenceTransformer BGE embedding engine
- `app/vector_store/`: VectorStore abstraction & NumpyVectorStore
- `app/retrieval.py`: BM25, RRF, intent boost, relevance gate
- `app/repository.py`: SQLite persistence (WAL mode, float32 BLOB vectors)
- `app/llm.py`: MultiProviderLLMClient (Gemini, Groq, OpenAI, Ollama)
- `app/rag.py`: RAGService orchestrator
- `app/main.py`: FastAPI application & routing
- `static/`: Frontend index.html, styles.css, app.js
- `tests/`: pytest test suites (unit, integration, multimodal, security, chaos)
