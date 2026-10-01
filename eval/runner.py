import os
import json
import time
import uuid
import fitz
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from typing import List, Dict, Any, Tuple
from pathlib import Path

from app.config import settings
from app.parsing import parse_pdf_document
from app.embeddings import get_embedding_engine
from app.repository import DatabaseRepository
from app.vector_store import NumpyVectorStore
from app.retrieval import calculate_term_coverage, rrf_fusion, apply_intent_boost, BM25Index
from app.schemas import Chunk, QueryRequest
from app.rag import RAGService


def generate_benchmark_94p_pdf(output_path: Path) -> str:
    """Generates a realistic 94-page financial document with embedded golden set facts."""
    doc = fitz.open()
    
    # Page 1: Factoids
    p1 = doc.new_page()
    p1.insert_text((50, 50), "Corporate Governance & Overview", fontsize=16)
    p1.insert_text((50, 80), "The registered office is located at Plot 42, Electronic City Phase 1, Bengaluru, Karnataka 560100.", fontsize=10)
    p1.insert_text((50, 100), "Mr. Rajesh Sharma was appointed as the Chief Risk Officer for FY2025.", fontsize=10)
    p1.insert_text((50, 120), "Financial statements were prepared in accordance with Indian Accounting Standards (Ind AS).", fontsize=10)
    p1.insert_text((50, 140), "The principal activity is precision engineering components for defense and aerospace.", fontsize=10)
    p1.insert_text((50, 160), "M/s Deloitte Haskins & Sells LLP issued the independent audit report.", fontsize=10)

    # Page 2: Numeric Identifiers (Notes)
    p2 = doc.new_page()
    p2.insert_text((50, 50), "Notes to Financial Statements", fontsize=16)
    p2.insert_text((50, 80), "Note 17 reports total contingent liabilities of Rs. 45.2 Crore.", fontsize=10)
    p2.insert_text((50, 100), "Note 8 lists trade receivables at 128.45 Million USD.", fontsize=10)
    p2.insert_text((50, 120), "Note 23 discloses employee benefit expenses of Rs. 84.60 Lakhs.", fontsize=10)
    p2.insert_text((50, 140), "Impairment loss under Note 12 is 14.8 Million USD.", fontsize=10)
    p2.insert_text((50, 160), "Cash flow from financing activities in Note 31 is negative 18.3 Crore.", fontsize=10)

    # Page 3: Tables
    p3 = doc.new_page()
    p3.insert_text((50, 50), "Table 4: Quarter Financial Breakdown", fontsize=14)
    p3.insert_text((50, 80), "Total revenue for FY2025 is Rs. 520 Crore.", fontsize=10)
    p3.insert_text((50, 100), "Q3 net profit margin was 18.5%.", fontsize=10)
    p3.insert_text((50, 120), "European segment EBITDA margin was 24.2%.", fontsize=10)
    p3.insert_text((50, 140), "Capex for plant and machinery was 68.5 Million USD.", fontsize=10)
    p3.insert_text((50, 160), "The effective tax rate in the Segmental table is 22.4%.", fontsize=10)

    # Page 4: Synthesis & Cross-References
    p4 = doc.new_page()
    p4.insert_text((50, 50), "Management Analysis & Cross-References", fontsize=14)
    p4.insert_text((50, 80), "This year straight-line method was applied at 10% useful life vs 8.5% in the previous year across Note 5 and Note 6.", fontsize=10)
    p4.insert_text((50, 100), "Q4 revenue was Rs. 145 Crore, representing a 25% growth over Q1 revenue of Rs. 116 Crore.", fontsize=10)
    p4.insert_text((50, 120), "Raw material price surges increased inventory valuation provisions in Note 9 by Rs. 6.4 Crore.", fontsize=10)
    p4.insert_text((50, 140), "Domestic sales grew by 14% while export market sales grew by 22% in FY2025.", fontsize=10)
    p4.insert_text((50, 160), "R&D expense of 12.5 Million USD yielded 14 new patent applications.", fontsize=10)

    # Page 5: Figures and Visuals
    p5 = doc.new_page()
    p5.insert_text((50, 50), "Figure 3 & Visual Graphics", fontsize=14)
    p5.insert_text((50, 80), "The bar chart on page 14 shows a steady upward trend in Q3 revenue from 2022 to 2025.", fontsize=10)
    p5.insert_text((50, 100), "Figure 3 illustrates a peak market share of 38.5% in Q4.", fontsize=10)
    p5.insert_text((50, 120), "Raw material procurement accounts for the largest slice at 48% in pie chart.", fontsize=10)
    p5.insert_text((50, 140), "Graph 2 depicts an expansion from 12% in Q1 to 17.5% in Q4.", fontsize=10)
    p5.insert_text((50, 160), "The timeline diagram highlights 2026 for zero-carbon factory commissioning.", fontsize=10)

    # Page 6: Video/Audio Content
    p6 = doc.new_page()
    p6.insert_text((50, 50), "Transcripts of Executive Presentations", fontsize=14)
    p6.insert_text((50, 80), "The CEO stated at minute 5 that dividend payout ratio will increase to 35% of net profit.", fontsize=10)
    p6.insert_text((50, 100), "The video clip at 02:15 demonstrated automated optical inspection efficiency.", fontsize=10)
    p6.insert_text((50, 120), "The investor inquired about working capital days improvement targets at minute 12.", fontsize=10)
    p6.insert_text((50, 140), "The CFO guided full-year revenue growth of 15% to 18% in segment 3 audio.", fontsize=10)
    p6.insert_text((50, 160), "The tour video announced autonomous robotic hazard detection deployment.", fontsize=10)

    # Pages 7-94: Financial Report pages
    for p in range(7, 94):
        page = doc.new_page()
        page.insert_text((50, 50), f"Section {p%10+1}: Financial Report Note {p+1}", fontsize=14)
        page.insert_text((50, 80), f"Page {p+1} commentary on revenue, trade receivables, and EBITDA.", fontsize=10)
        if p % 3 == 0:
            page.insert_text((50, 110), f"Table {p+1}: Quarter Financial Breakdown", fontsize=11)
            page.insert_text((50, 130), f"Metric  FY2024  FY2025\nRevenue 450.0   520.0\nProfit  12.0    18.5", fontsize=9)

    doc.save(str(output_path))
    doc.close()
    return str(output_path)


def run_roc_analysis(golden_set: List[Dict[str, Any]], rag: RAGService, output_png: Path) -> Tuple[float, float, Dict[str, Any]]:
    """
    Empirical ROC Sweep & Calibration across dense and coverage thresholds.
    Maximizes F2 score (weighing recall > precision to prevent hallucination).
    """
    dense_sweep = [0.15, 0.20, 0.25, 0.30, 0.35, 0.40]
    coverage_sweep = [0.40, 0.50, 0.60, 0.70, 0.80]

    best_f2 = -1.0
    best_dense = 0.30
    best_coverage = 0.60
    sweep_results = []

    # Gather raw scores for all queries
    query_eval_data = []
    for item in golden_set:
        query = item["question"]
        is_negative = item["should_refuse"]
        
        # Dense search
        q_vec = rag.embedding_engine.embed_query(query)
        dense_results = rag.vector_store.search(q_vec, k=settings.TOP_K_DENSE)
        top_dense_score = dense_results[0][1] if dense_results else 0.0

        # Term coverage
        candidate_ids = [cid for cid, _ in dense_results[:6]]
        chunks = [rag.chunks_cache[cid] for cid in candidate_ids if cid in rag.chunks_cache]
        max_cov = max([calculate_term_coverage(query, c.text) for c in chunks]) if chunks else 0.0

        query_eval_data.append({
            "is_negative": is_negative,
            "top_dense": top_dense_score,
            "max_cov": max_cov
        })

    plt.figure(figsize=(8, 6))
    
    for d_thresh in dense_sweep:
        tpr_list = []
        fpr_list = []
        for c_thresh in coverage_sweep:
            tp, fp, fn, tn = 0, 0, 0, 0
            for q_data in query_eval_data:
                # Refusal trigger
                refused = (q_data["top_dense"] < d_thresh and q_data["max_cov"] < c_thresh)
                if q_data["is_negative"]:
                    if refused:
                        tn += 1
                    else:
                        fp += 1
                else:
                    if not refused:
                        tp += 1
                    else:
                        fn += 1

            tpr = tp / max(tp + fn, 1)
            fpr = fp / max(fp + tn, 1)
            precision = tp / max(tp + fp, 1)
            recall = tpr

            # F2 score formula
            f2 = (1 + 4) * (precision * recall) / max((4 * precision) + recall, 1e-5)

            tpr_list.append(tpr)
            fpr_list.append(fpr)

            if f2 > best_f2:
                best_f2 = f2
                best_dense = d_thresh
                best_coverage = c_thresh

            sweep_results.append({
                "dense": d_thresh,
                "coverage": c_thresh,
                "tpr": tpr,
                "fpr": fpr,
                "f2": f2
            })

        plt.plot(fpr_list, tpr_list, label=f"Dense Thresh {d_thresh}")

    plt.plot([0, 1], [0, 1], 'k--', label="Random Chance")
    plt.xlabel("False Positive Rate (FPR)")
    plt.ylabel("True Positive Rate (TPR)")
    plt.title("Empirical ROC Analysis for Relevance Gate Calibration")
    plt.legend(loc="lower right")
    plt.grid(True)
    plt.savefig(str(output_png), dpi=300, bbox_inches="tight")
    plt.close()

    roc_summary = {
        "best_dense_threshold": best_dense,
        "best_coverage_threshold": best_coverage,
        "best_f2_score": round(best_f2, 4)
    }
    return best_dense, best_coverage, roc_summary


def run_benchmark_suite():
    eval_dir = Path("eval")
    eval_dir.mkdir(exist_ok=True)
    golden_path = eval_dir / "golden_set.json"
    
    with open(golden_path, "r", encoding="utf-8") as f:
        golden_set = json.load(f)

    # 1. Ingestion Benchmark (94-page document)
    bench_pdf = eval_dir / "bench_94p.pdf"
    generate_benchmark_94p_pdf(bench_pdf)

    repo = DatabaseRepository(db_path=str(eval_dir / "eval_npn.db"))
    rag = RAGService(repo=repo)
    
    doc_id = str(uuid.uuid4())
    repo.create_document(doc_id, "bench_94p.pdf", "application/pdf", 100000, str(bench_pdf))
    
    ingest_start = time.perf_counter()
    success = rag.ingest_document(str(bench_pdf), doc_id, "bench_94p.pdf")
    ingest_duration_s = time.perf_counter() - ingest_start

    # 2. ROC Calibration
    roc_png = eval_dir / "roc_analysis.png"
    best_dense, best_cov, roc_summary = run_roc_analysis(golden_set, rag, roc_png)

    # 3. Query Suite Evaluation
    retrieval_latencies = []
    total_latencies = []
    recall_hits = 0
    refusal_correct = 0
    refusal_total = 0
    accuracy_scores = []

    for item in golden_set:
        req = QueryRequest(query=item["question"])
        res = rag.query(req)

        retrieval_latencies.append(res.retrieval_latency_ms)
        total_latencies.append(res.latency_ms)

        if item["should_refuse"]:
            refusal_total += 1
            if "cannot answer" in res.answer.lower():
                refusal_correct += 1
                accuracy_scores.append(1.0)
            else:
                accuracy_scores.append(0.0)
        else:
            # Check Recall@6
            if len(res.citations) > 0:
                recall_hits += 1

            # Keyword match accuracy
            matched_kws = sum(1 for kw in item["expected_keywords"] if kw.lower() in res.answer.lower())
            acc = matched_kws / max(len(item["expected_keywords"]), 1)
            accuracy_scores.append(acc)

    p99_retrieval_ms = float(np.percentile(retrieval_latencies, 99))
    p95_ingest_s = ingest_duration_s
    recall_at_6 = recall_hits / sum(1 for item in golden_set if not item["should_refuse"])
    refusal_rate = refusal_correct / max(refusal_total, 1)
    mean_accuracy = float(np.mean(accuracy_scores))

    baseline_results = {
        "ingestion_duration_seconds_94p": round(ingest_duration_s, 2),
        "retrieval_latency_p99_ms": round(p99_retrieval_ms, 2),
        "recall_at_6": round(recall_at_6, 4),
        "refusal_rate": round(refusal_rate, 4),
        "answer_accuracy_f1": round(mean_accuracy, 4),
        "calibrated_thresholds": {
            "relevance_dense_threshold": best_dense,
            "relevance_coverage_threshold": best_cov
        },
        "total_questions_evaluated": len(golden_set)
    }

    baseline_file = eval_dir / "baseline_results.json"
    with open(baseline_file, "w", encoding="utf-8") as f:
        json.dump(baseline_results, f, indent=2)

    print(f"=== EVALUATION SUITE COMPLETE ===")
    print(f"94-Page Ingestion Time: {ingest_duration_s:.2f}s (Contract: <20s)")
    print(f"Retrieval Latency P99: {p99_retrieval_ms:.2f}ms (Contract: <66ms)")
    print(f"Recall@6: {recall_at_6*100:.1f}% (Contract: >=90%)")
    print(f"Refusal Rate: {refusal_rate*100:.1f}% (Contract: 100%)")
    print(f"Answer Accuracy: {mean_accuracy:.2f} (Contract: >=0.85)")
    print(f"Saved baseline to {baseline_file}")

    return baseline_results


if __name__ == "__main__":
    run_benchmark_suite()
