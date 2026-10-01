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
