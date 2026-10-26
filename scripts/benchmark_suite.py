import os
import sys
import time
import json
import platform
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Native Windows memory tracking
import ctypes
from ctypes import wintypes

class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
    _fields_ = [
        ('cb', wintypes.DWORD),
        ('PageFaultCount', wintypes.DWORD),
        ('PeakWorkingSetSize', ctypes.c_size_t),
        ('WorkingSetSize', ctypes.c_size_t),
        ('QuotaPeakPagedPoolUsage', ctypes.c_size_t),
        ('QuotaPagedPoolUsage', ctypes.c_size_t),
        ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t),
        ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
        ('PagefileUsage', ctypes.c_size_t),
        ('PeakPagefileUsage', ctypes.c_size_t),
    ]

def get_process_memory_mb() -> float:
    try:
        counters = PROCESS_MEMORY_COUNTERS()
        counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
        handle = ctypes.windll.kernel32.GetCurrentProcess()
        if ctypes.windll.psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
            return counters.WorkingSetSize / (1024 * 1024)
    except Exception:
        pass
    return 0.0


# Add repo root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.parsing import parse_pdf_document, extract_tables_from_page, profile_document_fonts
from app.embeddings import get_embedding_engine
from app.repository import DatabaseRepository
from app.vector_store import NumpyVectorStore
from app.retrieval import BM25Index, rrf_fusion, apply_intent_boost, calculate_term_coverage
from app.reranker import rerank, is_reranker_available
from app.schemas import Chunk, QueryRequest
from app.rag import RAGService


def benchmark_vector_store_scaling(vector_counts=[3000, 10000, 50000], dim=384, iterations=30) -> Dict[str, Any]:
    print("=" * 60)
    print("BENCHMARK: Vector Store & Retrieval Scaling (Exact NumPy Cosine)")
    print("=" * 60)
    results = {}

    for count in vector_counts:
        print(f"\n--- Benchmarking N = {count:,} vectors (dim={dim}) ---")
        mem_before = get_process_memory_mb()
        
        # 1. Construction
        t0 = time.perf_counter()
        vstore = NumpyVectorStore(dim=dim)
        
        # Generate random normalized float32 vectors
        np.random.seed(42)
        raw_vecs = np.random.randn(count, dim).astype(np.float32)
        norms = np.linalg.norm(raw_vecs, axis=1, keepdims=True)
        norm_vecs = raw_vecs / norms

        chunk_ids = [f"c_{i}" for i in range(count)]
        vstore.add(chunk_ids, norm_vecs, conversation_id="bench_conv")
        build_time_ms = (time.perf_counter() - t0) * 1000.0

        mem_after = get_process_memory_mb()
        mem_used_mb = mem_after - mem_before
        bytes_per_vector = (norm_vecs.nbytes) / count

        # 2. Search Latency
        search_latencies = []
        recalls = []

        # Ground truth check: pick 10 specific target vectors and search for them with small noise
        for q_idx in range(iterations):
            target_idx = (q_idx * 173) % count
            target_vec = norm_vecs[target_idx].copy()
            # Slight perturbation to simulate real query embedding
            noisy_q = target_vec + np.random.randn(dim).astype(np.float32) * 0.01
            noisy_q /= np.linalg.norm(noisy_q)

            t_start = time.perf_counter()
            top_results = vstore.search(noisy_q, k=30, conversation_id="bench_conv")
            t_search_ms = (time.perf_counter() - t_start) * 1000.0
            search_latencies.append(t_search_ms)

            # Check if true target is in top-1
            if top_results and top_results[0][0] == f"c_{target_idx}":
                recalls.append(1.0)
            else:
                recalls.append(0.0)

        cold_latency_ms = search_latencies[0]
        warm_latencies = search_latencies[1:]
        median_ms = float(np.median(warm_latencies))
        p95_ms = float(np.percentile(warm_latencies, 95))
        p99_ms = float(np.percentile(warm_latencies, 99))
        min_ms = float(np.min(warm_latencies))
        max_ms = float(np.max(warm_latencies))
        accuracy = float(np.mean(recalls)) * 100.0

        print(f"  Build Time:        {build_time_ms:.2f} ms")
        print(f"  Memory Added:      {mem_used_mb:.2f} MB ({bytes_per_vector:.1f} bytes/vec raw matrix)")
        print(f"  Cold Latency:      {cold_latency_ms:.3f} ms")
        print(f"  Warm Median:       {median_ms:.3f} ms")
        print(f"  Warm P95:          {p95_ms:.3f} ms")
        print(f"  Warm P99:          {p99_ms:.3f} ms")
        print(f"  Exact Recall@1:    {accuracy:.1f}%")

        results[str(count)] = {
            "vector_count": count,
            "dimension": dim,
            "build_time_ms": build_time_ms,
            "memory_mb": mem_used_mb,
            "bytes_per_vector": bytes_per_vector,
            "cold_latency_ms": cold_latency_ms,
            "median_latency_ms": median_ms,
            "p95_latency_ms": p95_ms,
            "p99_latency_ms": p99_ms,
            "min_latency_ms": min_ms,
            "max_latency_ms": max_ms,
            "exact_recall_p1": accuracy
        }

    return results


def benchmark_bm25_inverted_index(chunk_counts=[3000, 10000], iterations=30) -> Dict[str, Any]:
    print("\n" + "=" * 60)
    print("BENCHMARK: BM25 Inverted Index Retrieval Performance")
    print("=" * 60)
    results = {}

    vocab = [
        "revenue", "ebitda", "profit", "margin", "quarter", "fy2025", "operating",
        "turbine", "temperature", "kelvin", "cash", "debt", "equity", "growth",
        "expenses", "assets", "liabilities", "cloud", "pipeline", "cluster"
    ]

    for count in chunk_counts:
        print(f"\n--- BM25 with {count:,} chunks ---")
        bm25 = BM25Index()
        
        chunks = []
        np.random.seed(count)
        for i in range(count):
            # 20 to 50 tokens per chunk
            doc_terms = np.random.choice(vocab, size=np.random.randint(20, 50), replace=True)
            text = " ".join(doc_terms)
            chunks.append(Chunk(
                id=f"bm25_chunk_{i}",
                document_id="doc_bm25",
                filename="benchmark_report.pdf",
                page_number=(i % 100) + 1,
                section="Financials",
                content_type="text",
                text=text,
                context_text=text,
                conversation_id="conv_bm25"
            ))

        t_build_0 = time.perf_counter()
        bm25.add_chunks(chunks)
        build_time_ms = (time.perf_counter() - t_build_0) * 1000.0

        latencies = []
        sample_queries = [
            "operating revenue growth in fy2025",
            "ebitda margin and cash flow",
            "turbine temperature and cloud pipeline",
            "quarter liabilities and equity assets"
        ]

        for q_idx in range(iterations):
            q = sample_queries[q_idx % len(sample_queries)]
            t0 = time.perf_counter()
            res = bm25.search(q, top_k=30, conversation_id="conv_bm25")
            latencies.append((time.perf_counter() - t0) * 1000.0)

        cold_ms = latencies[0]
        warm = latencies[1:]
        median_ms = float(np.median(warm))
        p95_ms = float(np.percentile(warm, 95))
        p99_ms = float(np.percentile(warm, 99))

        print(f"  Build Time:        {build_time_ms:.2f} ms")
        print(f"  Cold Latency:      {cold_ms:.3f} ms")
        print(f"  Warm Median:       {median_ms:.3f} ms")
        print(f"  Warm P95:          {p95_ms:.3f} ms")
        print(f"  Warm P99:          {p99_ms:.3f} ms")

        results[str(count)] = {
            "chunk_count": count,
            "build_time_ms": build_time_ms,
            "cold_latency_ms": cold_ms,
            "median_latency_ms": median_ms,
            "p95_latency_ms": p95_ms,
            "p99_latency_ms": p99_ms
        }

    return results


def benchmark_ingestion_pipeline_breakdown(pdf_path: str) -> Dict[str, Any]:
    print("\n" + "=" * 60)
    print(f"BENCHMARK: Stage-by-Stage Ingestion Breakdown for {Path(pdf_path).name}")
    print("=" * 60)

    p = Path(pdf_path)
    file_size_bytes = p.stat().st_size
    file_size_mb = file_size_bytes / (1024 * 1024)

    import fitz
    doc = fitz.open(str(p))
    page_count = len(doc)
    doc.close()

    mem_start = get_process_memory_mb()
    t_start = time.perf_counter()

    # Stage 1: Font profiling & heading threshold
    t0 = time.perf_counter()
    doc = fitz.open(str(p))
    modal_size = profile_document_fonts(doc, sample_pages=settings.FONT_PROFILING_PAGES)
    doc.close()
    font_profiling_ms = (time.perf_counter() - t0) * 1000.0

    # Stage 2: PDF Parsing, Table Triage & Chunk Generation
    t0 = time.perf_counter()
    chunks = parse_pdf_document(str(p), "bench_doc_id")
    parsing_and_chunking_ms = (time.perf_counter() - t0) * 1000.0

    chunk_count = len(chunks)
    table_chunks = [c for c in chunks if c.content_type == "table"]
    prose_chunks = [c for c in chunks if c.content_type == "text"]

    # Stage 3: Embedding Batch Generation
    embedding_engine = get_embedding_engine()
    passage_texts = [c.text for c in chunks]

    t0 = time.perf_counter()
    vectors = embedding_engine.embed_passages(passage_texts)
    embedding_ms = (time.perf_counter() - t0) * 1000.0

    # Stage 4: Database Persistence (SQLite WAL Batch BLOBs)
    bench_db_path = settings.DATA_DIR / "bench_perf_temp.db"
    if bench_db_path.exists():
        try:
            bench_db_path.unlink()
        except Exception:
            pass

    repo = DatabaseRepository(db_path=str(bench_db_path))
    repo.create_document("bench_doc_id", p.name, "application/pdf", page_count, str(p), conversation_id="bench_conv")

    t0 = time.perf_counter()
    repo.insert_chunks_and_vectors(chunks, vectors, conversation_id="bench_conv")
    persistence_ms = (time.perf_counter() - t0) * 1000.0

    # Stage 5: Integrity Gate Check
    t0 = time.perf_counter()
    is_valid = repo.check_integrity_gate("bench_doc_id")
    integrity_ms = (time.perf_counter() - t0) * 1000.0

    total_ingest_time_s = time.perf_counter() - t_start
    mem_end = get_process_memory_mb()
    peak_mem_diff = mem_end - mem_start

    print(f"  File:                      {p.name}")
    print(f"  File Size:                 {file_size_mb:.2f} MB ({file_size_bytes:,} bytes)")
    print(f"  Page Count:                {page_count} pages")
    print(f"  Chunks Created:            {chunk_count} ({len(table_chunks)} tables, {len(prose_chunks)} prose)")
    print(f"  Font Profiling:            {font_profiling_ms:.2f} ms")
    print(f"  PDF Parsing & Extraction:  {parsing_and_chunking_ms:.2f} ms ({page_count / (parsing_and_chunking_ms / 1000.0):.1f} pages/sec)")
    print(f"  Embedding Generation:      {embedding_ms:.2f} ms ({chunk_count / (embedding_ms / 1000.0):.1f} chunks/sec)")
    print(f"  Database Batch Insert:     {persistence_ms:.2f} ms")
    print(f"  Integrity Gate Check:      {integrity_ms:.2f} ms (Passed: {is_valid})")
    print(f"  Total Ingestion Duration:  {total_ingest_time_s:.2f} s")
    print(f"  Process Memory Change:     {peak_mem_diff:.2f} MB")

    # Cleanup temp db
    try:
        bench_db_path.unlink(missing_ok=True)
    except Exception:
        pass

    return {
        "filename": p.name,
        "file_size_mb": file_size_mb,
        "page_count": page_count,
        "chunk_count": chunk_count,
        "table_chunk_count": len(table_chunks),
        "prose_chunk_count": len(prose_chunks),
        "font_profiling_ms": font_profiling_ms,
        "parsing_and_chunking_ms": parsing_and_chunking_ms,
        "embedding_ms": embedding_ms,
        "persistence_ms": persistence_ms,
        "integrity_check_ms": integrity_ms,
        "total_ingestion_seconds": total_ingest_time_s,
        "memory_delta_mb": peak_mem_diff,
        "pages_per_second": page_count / (parsing_and_chunking_ms / 1000.0) if parsing_and_chunking_ms > 0 else 0
    }


def benchmark_end_to_end_query_latency(iterations=20) -> Dict[str, Any]:
    print("\n" + "=" * 60)
    print("BENCHMARK: End-to-End Query & Retrieval Latency by Stage")
    print("=" * 60)

    embedding_engine = get_embedding_engine()
    vstore = NumpyVectorStore(dim=settings.EMBEDDING_DIM)
    bm25 = BM25Index()

    # Prepopulate with 3,000 chunks
    np.random.seed(42)
    sample_vecs = np.random.randn(3000, 384).astype(np.float32)
    sample_vecs /= np.linalg.norm(sample_vecs, axis=1, keepdims=True)

    chunks = []
    chunk_map = {}
    vocab = ["revenue", "margin", "quarter", "operating", "ebitda", "net", "profit", "fiscal", "tax", "cash"]
    for i in range(3000):
        terms = np.random.choice(vocab, size=25, replace=True)
        txt = f"Passage {i}: " + " ".join(terms)
        c = Chunk(
            id=f"c_{i}",
            document_id="doc_perf",
            filename="perf_report.pdf",
            page_number=(i % 50) + 1,
            section="Executive Highlights",
            content_type="text",
            text=txt,
            context_text=txt,
            conversation_id="conv_perf"
        )
        chunks.append(c)
        chunk_map[c.id] = c

    vstore.add([c.id for c in chunks], sample_vecs, conversation_id="conv_perf")
    bm25.add_chunks(chunks)

    query_str = "What was the operating revenue and net profit margin in the third quarter?"

    timings = {
        "query_embedding_ms": [],
        "vector_search_ms": [],
        "bm25_search_ms": [],
        "rrf_fusion_ms": [],
        "intent_boost_ms": [],
        "rerank_ms": [],
        "total_retrieval_ms": []
    }

    for _ in range(iterations):
        t_total_0 = time.perf_counter()

        # Stage 1: Asymmetric query embedding
        t0 = time.perf_counter()
        q_vec = embedding_engine.embed_query(query_str)
        t_embed = (time.perf_counter() - t0) * 1000.0

        # Stage 2: Exact NumPy Vector Search
        t0 = time.perf_counter()
        dense_res = vstore.search(q_vec, k=settings.TOP_K_DENSE, conversation_id="conv_perf")
        t_dense = (time.perf_counter() - t0) * 1000.0

        # Stage 3: BM25 Inverted Search
        t0 = time.perf_counter()
        sparse_res = bm25.search(query_str, top_k=settings.TOP_K_SPARSE, conversation_id="conv_perf")
        t_sparse = (time.perf_counter() - t0) * 1000.0

        # Stage 4: RRF Fusion
        t0 = time.perf_counter()
        fused = rrf_fusion(dense_res, sparse_res, k=settings.RRF_K)
        t_rrf = (time.perf_counter() - t0) * 1000.0

        # Stage 5: Intent Boost
        t0 = time.perf_counter()
        boosted = apply_intent_boost(query_str, fused, chunk_map)
        t_boost = (time.perf_counter() - t0) * 1000.0

        # Stage 5B: Cross-Encoder Rerank (top 12 to top 6)
        cands = [chunk_map[cid] for cid, _ in boosted[:settings.FINAL_TOP_K * 2] if cid in chunk_map]
        t0 = time.perf_counter()
        reranked = rerank(query_str, cands, top_k=settings.FINAL_TOP_K)
        t_rerank = (time.perf_counter() - t0) * 1000.0

        t_total = (time.perf_counter() - t_total_0) * 1000.0

        timings["query_embedding_ms"].append(t_embed)
        timings["vector_search_ms"].append(t_dense)
        timings["bm25_search_ms"].append(t_sparse)
        timings["rrf_fusion_ms"].append(t_rrf)
        timings["intent_boost_ms"].append(t_boost)
        timings["rerank_ms"].append(t_rerank)
        timings["total_retrieval_ms"].append(t_total)

    summary = {}
    for stage, vals in timings.items():
        warm = vals[1:]
        summary[stage] = {
            "cold_ms": vals[0],
            "median_ms": float(np.median(warm)),
            "p95_ms": float(np.percentile(warm, 95)),
            "p99_ms": float(np.percentile(warm, 99)),
            "min_ms": float(np.min(warm)),
            "max_ms": float(np.max(warm))
        }
        print(f"  {stage:<24}: Cold={vals[0]:.2f}ms | Median={np.median(warm):.2f}ms | P95={np.percentile(warm, 95):.2f}ms")

    return summary


def run_all_benchmarks():
    sys_info = {
        "os": f"{platform.system()} {platform.release()}",
        "python_version": platform.python_version(),
        "cpu_count": os.cpu_count(),
        "embedding_model": settings.EMBEDDING_MODEL_NAME,
        "embedding_dim": settings.EMBEDDING_DIM
    }
    print("=" * 60)
    print("INTELLIDOC 2.0 BENCHMARK SUITE")
    print("=" * 60)
    for k, v in sys_info.items():
        print(f"  {k}: {v}")

    # 1. Vector Store Scaling Benchmark
    vstore_results = benchmark_vector_store_scaling(vector_counts=[3000, 10000, 50000], iterations=30)

    # 2. BM25 Inverted Index Benchmark
    bm25_results = benchmark_bm25_inverted_index(chunk_counts=[3000, 10000], iterations=30)

    # 3. Query Retrieval Stage Breakdown
    query_results = benchmark_end_to_end_query_latency(iterations=25)

    # 4. Ingestion Breakdown on PDFs
    ingest_results = []
    # Test 94-page bench pdf
    bench_94p = Path("eval/bench_94p.pdf")
    if bench_94p.exists():
        ingest_results.append(benchmark_ingestion_pipeline_breakdown(str(bench_94p)))

    # Test small PDF
    small_pdf = Path("tests/fixtures/browser_test_summary.pdf")
    if small_pdf.exists():
        ingest_results.append(benchmark_ingestion_pipeline_breakdown(str(small_pdf)))

    # Test medium PDF if available
    med_pdf = Path("data/uploads/1e3de9e9-363d-487e-98a6-990eb4333dbe_Q226+Mgt+Report.pdf")
    if med_pdf.exists():
        ingest_results.append(benchmark_ingestion_pipeline_breakdown(str(med_pdf)))

    all_data = {
        "system_info": sys_info,
        "vector_store_scaling": vstore_results,
        "bm25_inverted_index": bm25_results,
        "query_retrieval_timings": query_results,
        "ingestion_breakdown": ingest_results,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

    out_file = Path("eval/benchmark_run_results.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2)

    print(f"\nBenchmark suite completed successfully. Results saved to {out_file}")
    return all_data


if __name__ == "__main__":
    run_all_benchmarks()
