# Project NPN (Narrative, Proof, Numbers)

**Project NPN** is a high-performance, local-first Retrieval-Augmented Generation (RAG) system engineered from scratch in Python for financial and technical document analysis.

---

## ⚡ Performance Contracts & Benchmarks

| Metric | Target / Benchmark | Achieved Engine Performance |
|--------|-------------------|-----------------------------|
| **PDF Ingestion Speed** | 94 pages in <20s (17.2s target) | **~14.5s** (7-stage pipeline) |
| **Vector Search Latency** | <100ms for 3,000 vectors | **~8.2ms** (NumPy exact brute-force cosine) |
| **Vector Storage Footprint** | Raw `float32` BLOBs | **1.5 KB per vector** (vs 22 KB JSON) |
| **Relevance & Refusal** | Dual relevance gate | **Strict refusal** on unevidenced queries |

---

## 🏗️ Architectural Core (No LLM Orchestration Frameworks)

1. **No Frameworks**: 100% custom, profilable Python code without LangChain, LlamaIndex, Haystack, or FAISS.
2. **Exact Brute-Force Cosine**: NumPy matrix multiplication (`matrix @ query_vec.T`) over normalized float32 vectors.
3. **SQLite WAL + BLOB Storage**: Raw `float32` binary BLOB storage loaded into memory at startup.
4. **Asymmetric Embedding**:
   - Passages are embedded bare using `BAAI/bge-small-en-v1.5`.
   - Queries are prefixed with `"Represent this sentence for searching relevant passages: "`.
5. **Dual-Text Chunk Model**:
   - `text`: Linearized search text optimized for findability and BM25 indexing.
   - `context_text`: Markdown grid and structured surrounding text optimized for LLM readability.
6. **7-Stage Ingestion Pipeline**:
   - STAGE 0: Instant HTTP 202 ACCEPT
   - STAGE 1: Font profiling (modal size calculation & heading detection)
   - STAGE 2: Text span routing + ~8ms Table Triage filter (`page_probably_has_table`)
   - STAGE 3: Heading carry-over
   - STAGE 4: Batch L2-normalized vector embedding
   - STAGE 5: SQLite batch persist & in-memory matrix append
   - STAGE 6: Integrity Gate (`count(chunks) == count(vectors)`)
   - STAGE 7: Background multimedia attachment processing (video keyframes, audio transcript windows, vision captions)

---

## 📁 Repository Structure

```
QA/
├── app/
│   ├── __init__.py
│   ├── config.py          # Environment settings & thresholds
│   ├── schemas.py         # Chunk dataclass & Pydantic API contracts
│   ├── parsing.py         # PyMuPDF font profiling, table triage & extraction
│   ├── embeddings.py      # BAAI/bge-small-en-v1.5 local engine
│   ├── retrieval.py       # NumPy VectorIndex, custom BM25, RRF, Intent Boost
│   ├── repository.py      # SQLite WAL DB repo & vector BLOB operations
│   ├── llm.py             # Multi-provider LLM client (Gemini, Groq, OpenAI, Ollama)
│   ├── multimedia.py      # Video keyframe extractor, audio transcript segmenter
│   ├── rag.py             # RAGService orchestrator
│   └── main.py            # FastAPI HTTP endpoints & static mounting
├── static/
│   ├── index.html         # Dark glassmorphic user interface
│   ├── styles.css         # Typography, animations, and layouts
│   └── app.js             # Drag & drop upload, polling, chat UI & citation modal
├── tests/
│   ├── test_unit.py       # Font profiling, table triage, BLOB size, RRF, BM25
│   ├── test_integration.py# Ingestion timing contract, retrieval latency, SQLite WAL
│   ├── test_multimodal.py # Video keyframes, audio transcript windows, dual-text
│   └── test_security_and_contracts.py # Script escaping, temp=0, relevance gate refusal
├── Dockerfile             # Multi-stage image build baking embedding weights
├── requirements.txt       # Production dependencies with exact versions
└── README.md
```

---

## 🛠️ Quickstart & Local Setup

### 1. Environment Template (`.env`)
Create a `.env` file in the project root:

```env
DEFAULT_LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key_here
GROQ_API_KEY=your_groq_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
OLLAMA_BASE_URL=http://localhost:11434/v1
```

### 2. Install Dependencies & Run Server
```bash
# Install exact requirements
pip install -r requirements.txt

# Run Uvicorn ASGI Server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Open browser at `http://127.0.0.1:8000` to interact with the glassmorphic web dashboard.

---

## 🧪 Running the Test Suite (30 Tests)

Execute the complete 30-test suite covering unit logic, timing contracts, integrity gates, and security:

```bash
python -m pytest -v
```

---

## 🐳 Docker Deployment

```bash
# Build Docker Image (Bakes embedding model weights)
docker build -t project-npn:latest .

# Run Container
docker run -d -p 8000:8000 --env-file .env project-npn:latest
```
