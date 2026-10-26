import time
import sys
import numpy as np
from typing import List, Dict, Tuple
from pathlib import Path

from app.config import settings
from app.schemas import Chunk
from app.vector_store import NumpyVectorStore
from app.retrieval import BM25Index, rrf_fusion
from app.embeddings import get_embedding_engine


def generate_synthetic_corpus(num_chunks: int, num_docs: int = 10) -> Tuple[List[Chunk], np.ndarray, Dict[str, List[str]]]:
    """Generates synthetic chunks and float32 normalized vectors partitioned across documents."""
    dim = settings.EMBEDDING_DIM
    chunks: List[Chunk] = []
    rng = np.random.RandomState(42)

    raw_vecs = rng.randn(num_chunks, dim).astype(np.float32)
    norms = np.linalg.norm(raw_vecs, axis=1, keepdims=True)
    vectors = raw_vecs / np.maximum(norms, 1e-9)

    doc_ids = [f"doc_{i % num_docs}" for i in range(num_chunks)]
    doc_chunk_map: Dict[str, List[str]] = {}

    topics = [
        "financial audit revenue EBITDA quarterly earnings operating margins balance sheet cash flow statement",
        "cloud infrastructure microservices kubernetes docker autoscaling distributed compute nodes pod cluster",
        "security zero trust IAM authorization encryption tokens compliance HIPAA GDPR firewall proxy",
        "database replication WAL sqlite postgresql sharding index latency read replicas concurrency",
        "machine learning transformers attention embeddings cross encoder reranking vectors retrieval cosine"
    ]

    for i in range(num_chunks):
        did = doc_ids[i]
        cid = f"chk_{did}_{i}"
        doc_chunk_map.setdefault(did, []).append(cid)
        topic = topics[i % len(topics)]
        text = f"Section {i} for {did}. {topic}. Specific parameter code_{i} and metric {i * 1.5:.2f} units."

        chunks.append(Chunk(
            id=cid,
            document_id=did,
            filename=f"{did}.pdf",
            page_number=(i % 20) + 1,
            section=f"Section_{i}",
            content_type="text",
            text=text,
            context_text=text,
            conversation_id="conv_bench"
        ))

    return chunks, vectors, doc_chunk_map


def run_benchmark():
    print("=" * 78)
    print("IntelliDoc — Strict Scoped Retrieval Performance & Cross-Document Isolation Benchmark")
    print("=" * 78)

    embedder = get_embedding_engine()
    test_query = "What are the quarterly financial earnings and operating margins?"

    # 1. Query Embedding Time
    t_embed_runs = []
    for _ in range(10):
        t0 = time.perf_counter()
        query_vec = embedder.embed_query(test_query)
        t_embed_runs.append((time.perf_counter() - t0) * 1000.0)
    avg_embed_ms = np.mean(t_embed_runs)
    print(f"\n[Stage 1] Query Embedding Latency: {avg_embed_ms:.2f} ms (p95: {np.percentile(t_embed_runs, 95):.2f} ms)")

    vector_counts = [100, 500, 2000, 5000]
    num_docs = 10
    selected_doc_ids = ["doc_0", "doc_1"]  # 20% of corpus scope

    results_table = []

    for N in vector_counts:
        chunks, vectors, doc_map = generate_synthetic_corpus(N, num_docs=num_docs)

        # Initialize stores
        vstore = NumpyVectorStore(dim=settings.EMBEDDING_DIM)
        vstore.upsert(chunks, vectors)

        bm25 = BM25Index()
        bm25.add_chunks(chunks)

        # --- A. Filter Preparation Time ---
        t_prep_runs = []
        for _ in range(50):
            t0 = time.perf_counter()
            matching_indices = []
            for did in selected_doc_ids:
                indices = vstore.doc_index_map.get(did)
                if indices:
                    matching_indices.extend(indices)
            t_prep_runs.append((time.perf_counter() - t0) * 1000.0)
        avg_filter_prep_ms = np.mean(t_prep_runs)

        # --- B. Vector Search: Scoped vs Unscoped ---
        t_v_scoped_runs = []
        for _ in range(50):
            t0 = time.perf_counter()
            res_v_scoped = vstore.search(query_vec, k=10, document_ids=selected_doc_ids)
            t_v_scoped_runs.append((time.perf_counter() - t0) * 1000.0)
        avg_v_scoped_ms = np.mean(t_v_scoped_runs)

        t_v_unscoped_runs = []
        for _ in range(50):
            t0 = time.perf_counter()
            res_v_unscoped = vstore.search(query_vec, k=10)
            t_v_unscoped_runs.append((time.perf_counter() - t0) * 1000.0)
        avg_v_unscoped_ms = np.mean(t_v_unscoped_runs)

        # --- C. BM25 Search: Scoped vs Unscoped ---
        t_bm_scoped_runs = []
        for _ in range(50):
            t0 = time.perf_counter()
            res_bm_scoped = bm25.search(test_query, top_k=10, document_ids=selected_doc_ids)
            t_bm_scoped_runs.append((time.perf_counter() - t0) * 1000.0)
        avg_bm_scoped_ms = np.mean(t_bm_scoped_runs)

        t_bm_unscoped_runs = []
        for _ in range(50):
            t0 = time.perf_counter()
            res_bm_unscoped = bm25.search(test_query, top_k=10)
            t_bm_unscoped_runs.append((time.perf_counter() - t0) * 1000.0)
        avg_bm_unscoped_ms = np.mean(t_bm_unscoped_runs)

        # --- D. RRF Fusion Time ---
        t_rrf_runs = []
        for _ in range(50):
            t0 = time.perf_counter()
            fused = rrf_fusion(res_v_scoped, res_bm_scoped, k=60)
            t_rrf_runs.append((time.perf_counter() - t0) * 1000.0)
        avg_rrf_ms = np.mean(t_rrf_runs)

        # --- E. Total Retrieval Latency ---
        total_scoped_ms = avg_filter_prep_ms + avg_v_scoped_ms + avg_bm_scoped_ms + avg_rrf_ms
        total_unscoped_ms = avg_v_unscoped_ms + avg_bm_unscoped_ms + avg_rrf_ms

        # --- F. Scope Precision & Leakage Verification ---
        scoped_chunks_allowed = set(doc_map["doc_0"] + doc_map["doc_1"])
        retrieved_scoped_cids = [cid for cid, _ in fused]
        scoped_precision = sum(1 for cid in retrieved_scoped_cids if cid in scoped_chunks_allowed) / max(len(retrieved_scoped_cids), 1)

        unscoped_fused = rrf_fusion(res_v_unscoped, res_bm_unscoped, k=60)
        unscoped_cids = [cid for cid, _ in unscoped_fused]
        unscoped_leakage = sum(1 for cid in unscoped_cids if cid not in scoped_chunks_allowed) / max(len(unscoped_cids), 1)

        # --- G. Memory Overhead ---
        matrix_bytes = vectors.nbytes
        map_overhead_bytes = sys.getsizeof(vstore.doc_index_map) + sys.getsizeof(vstore.doc_id_map)
        overhead_pct = (map_overhead_bytes / matrix_bytes) * 100.0

        results_table.append({
            "N": N,
            "filter_prep_ms": avg_filter_prep_ms,
            "v_scoped_ms": avg_v_scoped_ms,
            "v_unscoped_ms": avg_v_unscoped_ms,
            "bm_scoped_ms": avg_bm_scoped_ms,
            "bm_unscoped_ms": avg_bm_unscoped_ms,
            "rrf_ms": avg_rrf_ms,
            "total_scoped_ms": total_scoped_ms,
            "total_unscoped_ms": total_unscoped_ms,
            "scoped_precision": scoped_precision * 100.0,
            "unscoped_leakage": unscoped_leakage * 100.0,
            "overhead_pct": overhead_pct
        })

    print("\n--- DETAILED BENCHMARK RESULTS ---")
    print(f"{'Corpus N':<10} | {'Filter Prep':<12} | {'Vector Scoped':<14} | {'Vector Unscoped':<16} | {'BM25 Scoped':<12} | {'BM25 Unscoped':<14} | {'RRF':<8} | {'Total Scoped':<13} | {'Precision':<10} | {'Leakage Risk'}")
    print("-" * 140)
    for r in results_table:
        print(
            f"{r['N']:<10} | "
            f"{r['filter_prep_ms']:>8.4f} ms  | "
            f"{r['v_scoped_ms']:>10.4f} ms  | "
            f"{r['v_unscoped_ms']:>12.4f} ms  | "
            f"{r['bm_scoped_ms']:>8.4f} ms  | "
            f"{r['bm_unscoped_ms']:>10.4f} ms  | "
            f"{r['rrf_ms']:>5.3f} ms | "
            f"{r['total_scoped_ms']:>9.4f} ms  | "
            f"{r['scoped_precision']:>8.1f}%  | "
            f"{r['unscoped_leakage']:>8.1f}% unscoped leakage"
        )

    print("\nBenchmark completed successfully.")


if __name__ == "__main__":
    run_benchmark()
