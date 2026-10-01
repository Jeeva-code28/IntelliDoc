# Original User Request

## Initial Request — 2026-08-14T16:39:39Z

You are the Project Orchestrator for enhancing the Project NPN local-first RAG system.
Your working directory is D:/QA/QA/.agents/teamwork_preview_orchestrator_1/.
The project root is D:/QA/QA.
The authoritative specification is in D:/QA/QA/ORIGINAL_REQUEST.md and D:/QA/ARCHITECTURE.md.

User Request Summary:
Enhance the Project NPN local-first RAG system based on ARCHITECTURE.md so that it comprehensively understands, indexes, and evaluates the relevance of all attached and embedded file formats in PDFs (including images, video, audio recordings, tables, and documents) to enable grounded multimodal Q&A and proof citations through the web interface.

Key Requirements:
- R1. Multimodal PDF & Attachment Extraction Engine (PyMuPDF, image captions, video temporal scenes/keyframes, audio temporal transcript windows, dual-text representation text/context_text, cross-page table merge, bbox spatial coordinates).
- R2. Cross-Modal Hybrid Retrieval & Relevance Gating (NumPy exact vector search + BM25 sparse index + RRF k=60, intent boosting, dual semantic threshold + term coverage relevance gate).
- R3. Grounded Multimodal Generation & Claim Verification API (FastAPI endpoints /api/documents/upload, /api/query, /api/documents/{id}, /health, grounded multi-source synthesis with [S1],[S2], claim verification badges supported/partial/unsupported, sub-100ms vector retrieval SQLite float32 BLOB + in-memory indexes).
- R4. Interactive Multimodal Web Interface (PDF upload dropzone + progress, chat interface + latency metrics + badges, interactive citation drawer / media cards / modal view / bounding box highlights / image previews / video/audio timestamps).
- Full 100% passing test suite across unit, integration, and multimodal test suites.

Please plan, decompose, dispatch to specialized worker subagents, coordinate, review, verify with tests, maintain progress.md and BRIEFING.md, and deliver a comprehensive solution. When complete, report back with your completion summary.

## 2026-08-15T15:40:02+05:30

Implement a conversation-scoped multimodal knowledge base and chat system for Project NPN with strict zero cross-conversation document bleed/spillover, support for multiple large files per conversation, seamless conversation switching/resumption in the UI and backend, and comprehensive automated backend and real-time browser test verification.

Working directory: d:/QA/QA
Integrity mode: development

## Requirements

### R1. Conversation-Scoped Document Architecture & Storage Isolation
- Associate every uploaded document, chunk, and vector embedding strictly with its target `conversation_id` (supporting 1 or multiple files per conversation).
- Update SQLite schemas and repository methods so documents, chunks, and float32 BLOB vectors can be indexed, retrieved, and deleted with conversation-level isolation.
- When returning to an existing conversation and uploading new documents, append to that conversation's specific knowledge base without affecting any other conversation.

### R2. Strict Zero-Spillover Hybrid Retrieval & RAG Query Execution
- Filter dense vector search (`NumpyVectorStore`), sparse BM25 indexing (`BM25Index`), and reciprocal rank fusion (`RRF`) strictly to the active `conversation_id`.
- Ensure queries executed within Conversation A strictly search only Conversation A's documents, with mathematical and programmatic guarantees of zero leak/spillover from Conversation B or C.
- Maintain grounded generation (temperature=0), fact-checking verification auditing, and source citations (`[S1]`, `[S2]`) isolated to the conversation's active documents.

### R3. Large File Size Support & Local Privacy
- Optimize document parsing, batch embedding, and vector persistence for large documents/media to overcome standard cloud/ChatGPT file size constraints without memory exhaustion.
- Preserve 100% local-first privacy: all document parsing, embeddings, SQLite storage, and local Ollama inference execute strictly on-device without external data egress unless cloud providers are explicitly selected.

### R4. Multi-Conversation Web Workspace & Frontend UI
- Update the dark glassmorphic interface (`static/index.html`, `static/app.js`, `static/styles.css`) with a sidebar/drawer for conversation management:
  - Create new conversations with one click.
  - Switch seamlessly between past conversations, loading that conversation's specific message history and document list.
  - Upload 1 or more files directly into the currently active conversation with real-time progress indicators.
  - Display active conversation status, document count badge, latency badges, and citation previews.

### R5. Comprehensive Backend & Real-Time Browser Testing
- Implement automated pytest test suites validating:
  - Multi-file ingestion across multiple independent conversations.
  - Strict zero spillover: verify questions in Conversation A cannot retrieve or cite documents from Conversation B.
  - Conversation resumption: verify uploading a new file in Conversation A expands its knowledge base while leaving Conversation B isolated.
  - Large document ingestion performance and integrity gate validation.
- Perform live browser-based testing on `http://localhost:8000`:
  - Test creating Conversation 1, uploading Document 1, querying Document 1.
  - Test creating Conversation 2, uploading Document 2, querying Document 2, and verifying zero Document 1 citations.
  - Test switching back to Conversation 1, uploading Document 3, and verifying answers draw strictly from Documents 1 & 3.

## Acceptance Criteria

### Data & Retrieval Isolation
- [ ] Database repository and vector stores strictly partition documents, chunks, and vectors by `conversation_id`.
- [ ] Retrieval in Conversation A returns 0 chunks and 0 citations from Conversation B, confirmed by automated cross-conversation leak tests.
- [ ] Uploading additional documents to an existing conversation correctly appends to that conversation's knowledge base without cross-talk.

### Performance & File Capacity
- [ ] Ingestion of multi-page / large documents completes smoothly with progress updates and integrity gate checks (`chunks == vectors`).
- [ ] Dense + sparse hybrid retrieval maintains sub-50ms latency within the conversation's vector partition.

### Frontend User Experience
- [ ] User can create new conversations, see conversation list in sidebar, and switch between conversations without page reload.
- [ ] Document list, chat messages, and citation drawer dynamically update to match the active conversation.

### Verification & Test Pass
- [ ] 100% pass across all unit, integration, isolation, and security test suites.
- [ ] Real-time browser testing validates end-to-end conversation creation, switching, isolated multi-file upload, and citation inspection.

