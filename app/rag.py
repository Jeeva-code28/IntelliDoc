import time
import uuid
from typing import List, Dict, Tuple, Optional, Any
from pathlib import Path

from app.config import settings
from app.schemas import (
    Chunk, QueryRequest, QueryResponse, CitationSource, VerificationBadge
)
from app.parsing import parse_pdf_document, sandbox_extract_zip_attachment
from app.multimedia import get_multimedia_processor
from app.embeddings import get_embedding_engine
from app.repository import DatabaseRepository, get_repository
from app.vector_store import VectorStore, NumpyVectorStore
from app.retrieval import (
    BM25Index, calculate_term_coverage, rrf_fusion, apply_intent_boost
)
from app.llm import get_llm_client, MultiProviderLLMClient
from app.observability.logging import log_ingestion_complete, log_query_served, logger


class RAGService:
    """
    Core Orchestrator for Project NPN.
    Integrates 7-stage Ingestion, VectorStore abstraction, Hybrid Retrieval (RRF + Intent Boost),
    Relevance Gate, Grounded LLM Generation, and Verification Audit.
    """

    def __init__(self, repo: Optional[DatabaseRepository] = None, vector_store: Optional[VectorStore] = None):
        self.repo = repo or get_repository()
        self.vector_store: VectorStore = vector_store or NumpyVectorStore(dim=settings.EMBEDDING_DIM)
        self.embedding_engine = get_embedding_engine()
        self.bm25_index = BM25Index(k1=settings.BM25_K1, b=settings.BM25_B)
        self.llm_client = get_llm_client()
        self.chunks_cache: Dict[str, Chunk] = {}
        self.initialized = False

    def initialize_indexes(self):
        """Loads chunks and float32 BLOB vectors from SQLite into memory on startup."""
        if self.initialized:
            return

        logger.info("rag_service_initializing_indexes")
        all_chunks = self.repo.load_all_chunks()
        self.chunks_cache = {c.id: c for c in all_chunks}

        chunk_ids, matrix = self.repo.load_all_vectors()
        if len(all_chunks) > 0 and matrix.shape[0] > 0:
            ordered_chunks = [self.chunks_cache[cid] for cid in chunk_ids if cid in self.chunks_cache]
            self.vector_store.clear()
            self.vector_store.upsert(ordered_chunks, matrix)

            self.bm25_index.clear()
            self.bm25_index.add_chunks(all_chunks)

        self.initialized = True
        logger.info("rag_service_indexes_ready", chunk_count=len(self.chunks_cache))

    def ingest_document(self, file_path: str, doc_id: str, original_filename: str) -> bool:
        """
        Ingests PDF documents or standalone multimedia attachments (video, audio, image, tabular CSV, zip).
        """
        start_time = time.perf_counter()

        try:
            existing_doc = self.repo.get_document(doc_id)
            if not existing_doc:
                self.repo.create_document(
                    doc_id=doc_id,
                    filename=original_filename,
                    file_type="application/pdf" if file_path.lower().endswith(".pdf") else "application/octet-stream",
                    page_count=0,
                    file_path=file_path
                )

            self.repo.update_document_status(doc_id, "processing", progress=0.1)
            ext = Path(file_path).suffix.lower()
            multimedia = get_multimedia_processor()

            # Multimodal parsing router
            if ext == ".pdf":
                chunks = parse_pdf_document(file_path, doc_id)
            elif ext in [".mp4", ".mov", ".avi", ".webm", ".mkv"]:
                chunks = multimedia.process_video_file(file_path, doc_id, original_filename)
            elif ext in [".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac"]:
                chunks = multimedia.process_audio_file(file_path, doc_id, original_filename)
            elif ext in [".png", ".jpg", ".jpeg", ".webp", ".svg", ".bmp", ".tiff"]:
                chunks = multimedia.process_image_attachment(file_path, doc_id, original_filename)
            elif ext in [".csv", ".tsv"]:
                chunks = multimedia.process_tabular_attachment(file_path, doc_id, original_filename)
            elif ext == ".zip":
                is_quarantined, bad_files = sandbox_extract_zip_attachment(Path(file_path), doc_id)
                content_type = "attachment_quarantined" if is_quarantined else "attachment"
                chunks = [
                    Chunk(
                        id=str(uuid.uuid4()),
                        document_id=doc_id,
                        filename=original_filename,
                        page_number=1,
                        section="Archives",
                        content_type=content_type,
                        text=f"[{content_type.capitalize()}] Archive {original_filename}",
                        context_text=f"Uploaded ZIP Archive: {original_filename}. Quarantined: {is_quarantined}",
                        bbox=None,
                        asset_path=str(file_path),
                        temporal_start=None,
                        temporal_end=None,
                        metadata={"filename": original_filename, "quarantined": is_quarantined}
                    )
                ]
            else:
                # Default text extraction
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    txt = f.read()
                chunks = [
                    Chunk(
                        id=str(uuid.uuid4()),
                        document_id=doc_id,
                        filename=original_filename,
                        page_number=1,
                        section="Document Text",
                        content_type="text",
                        text=f"{original_filename}. {txt[:500]}",
                        context_text=f"Document {original_filename}:\n\n{txt}",
                        bbox=None,
                        asset_path=None,
                        temporal_start=None,
                        temporal_end=None,
                        metadata={"length": len(txt)}
                    )
                ]

            self.repo.update_document_status(doc_id, "processing", progress=0.5)

            if not chunks:
                self.repo.update_document_status(doc_id, "failed", error="No chunks extracted from document.")
                return False

            # Stage 4: Embed passages (bare text without query prefix)
            passage_texts = [c.text for c in chunks]
            vectors = self.embedding_engine.embed_passages(passage_texts)
            self.repo.update_document_status(doc_id, "processing", progress=0.8)

            # Stage 5: SQLite Batch Insert (float32 BLOBs)
            self.repo.insert_chunks_and_vectors(chunks, vectors)

            # Stage 6: Integrity Gate Check
            is_valid = self.repo.check_integrity_gate(doc_id)
            if not is_valid:
                self.repo.update_document_status(doc_id, "failed", error="Integrity gate check failed: chunk_count != vector_count.")
                return False

            # Update in-memory vector store & BM25 index
            for c in chunks:
                self.chunks_cache[c.id] = c
            self.vector_store.upsert(chunks, vectors)
            self.bm25_index.add_chunks(chunks)

            self.repo.update_document_status(doc_id, "ready", progress=1.0)
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            log_ingestion_complete(
                doc_id=doc_id,
                duration_ms=elapsed_ms,
                page_count=max(c.page_number for c in chunks) if chunks else 1,
                table_count=sum(1 for c in chunks if c.content_type == "table"),
                chunk_count=len(chunks)
            )
            return True

        except Exception as e:
            logger.error("ingestion_error", doc_id=doc_id, error=str(e))
            self.repo.update_document_status(doc_id, "failed", error=str(e))
            return False

    def query(self, req: QueryRequest) -> QueryResponse:
        start_total = time.perf_counter()

        if not self.initialized:
            self.initialize_indexes()

        conv_id = req.conversation_id or str(uuid.uuid4())
        if not req.conversation_id:
            self.repo.create_conversation(conv_id)

        # STAGE 1: Fast Asymmetric Embed Query (<15ms)
        start_retrieval = time.perf_counter()
        query_vec = self.embedding_engine.embed_query(req.query)

        # STAGE 2: Exact NumPy Vector Search (<25ms P99)
        dense_results = self.vector_store.search(query_vec, k=settings.TOP_K_DENSE)

        # STAGE 3: Custom BM25 Sparse Search (<5ms)
        sparse_results = self.bm25_index.search(req.query, top_k=settings.TOP_K_SPARSE)

        # STAGE 4: RRF Fusion (k=60)
        fusion_results = rrf_fusion(dense_results, sparse_results, k=settings.RRF_K)

        # STAGE 5: Intent Boost (numeric/table, video, audio, image boost)
        boosted_results = apply_intent_boost(req.query, fusion_results, self.chunks_cache)
        retrieval_latency_ms = (time.perf_counter() - start_retrieval) * 1000.0

        top_candidates = boosted_results[:settings.FINAL_TOP_K]

        # STAGE 6: Dual Relevance Gate
        top_dense_score = dense_results[0][1] if dense_results else 0.0
        candidate_chunks = [self.chunks_cache[cid] for cid, _ in top_candidates if cid in self.chunks_cache]

        max_term_coverage = max(
            [calculate_term_coverage(req.query, c.text) for c in candidate_chunks]
        ) if candidate_chunks else 0.0

        injection_keywords = ["ignore all", "system prompt", "admin mode", "dan prompt", "unrestrained", "bypass network"]
        has_injection = any(kw in req.query.lower() for kw in injection_keywords)

        refusal_triggered = (
            has_injection or
            max_term_coverage == 0.0 or
            (max_term_coverage < settings.RELEVANCE_COVERAGE_THRESHOLD and top_dense_score < 0.68) or
            top_dense_score < settings.RELEVANCE_DENSE_THRESHOLD
        )

        if refusal_triggered or not candidate_chunks:
            refusal_text = "I cannot answer this based on the provided document."
            total_latency_ms = (time.perf_counter() - start_total) * 1000.0

            log_query_served(
                query=req.query,
                latency_ms=total_latency_ms,
                retrieval_latency_ms=retrieval_latency_ms,
                chunks_retrieved=0,
                provider_used="none_refusal"
            )

            v_badge = VerificationBadge(
                status="supported",
                reasoning="Relevance gate blocked unevidenced query.",
                supported_claims=[],
                unsupported_claims=[]
            )

            msg_id = str(uuid.uuid4())
            self.repo.add_message(msg_id, conv_id, "user", req.query, [])
            self.repo.add_message(str(uuid.uuid4()), conv_id, "assistant", refusal_text, [])

            return QueryResponse(
                answer=refusal_text,
                citations=[],
                verification=v_badge,
                latency_ms=total_latency_ms,
                retrieval_latency_ms=retrieval_latency_ms,
                conversation_id=conv_id
            )

        # STAGE 7: Grounded LLM Context Construction
        context_parts = []
        citations: List[CitationSource] = []
        citation_ids = []

        for idx, chunk in enumerate(candidate_chunks, start=1):
            source_tag = f"[S{idx}]"
            context_parts.append(f"SOURCE {source_tag} ({chunk.filename}, type: {chunk.content_type}, p.{chunk.page_number}, {chunk.section}):\n{chunk.context_text}")
            citation_ids.append(chunk.id)

            # Cosine score lookup
            score = next((sc for cid, sc in dense_results if cid == chunk.id), 0.0)
            citations.append(CitationSource(
                chunk_id=chunk.id,
                filename=chunk.filename,
                page_number=chunk.page_number,
                section=chunk.section,
                content_type=chunk.content_type,
                snippet=chunk.context_text[:500] if len(chunk.context_text) > 500 else chunk.context_text,
                score=float(score),
                bbox=chunk.bbox,
                asset_path=chunk.asset_path,
                temporal_start=chunk.temporal_start,
                temporal_end=chunk.temporal_end
            ))

        formatted_context = "\n\n".join(context_parts)

        # STAGE 8 & 9: LLM Generation & Verification Audit
        answer, provider_used = self.llm_client.generate_grounded_answer(
            query=req.query,
            formatted_context=formatted_context,
            provider=req.llm_provider
        )

        verification_badge = self.llm_client.verify_answer(
            query=req.query,
            answer=answer,
            formatted_context=formatted_context,
            provider=req.llm_provider
        )

        total_latency_ms = (time.perf_counter() - start_total) * 1000.0

        log_query_served(
            query=req.query,
            latency_ms=total_latency_ms,
            retrieval_latency_ms=retrieval_latency_ms,
            chunks_retrieved=len(citations),
            provider_used=provider_used
        )

        # Persist conversation turn
        self.repo.add_message(str(uuid.uuid4()), conv_id, "user", req.query, [])
        self.repo.add_message(str(uuid.uuid4()), conv_id, "assistant", answer, citation_ids)

        return QueryResponse(
            answer=answer,
            citations=citations,
            verification=verification_badge,
            latency_ms=total_latency_ms,
            retrieval_latency_ms=retrieval_latency_ms,
            conversation_id=conv_id
        )


_rag_service = None


def get_rag_service() -> RAGService:
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
