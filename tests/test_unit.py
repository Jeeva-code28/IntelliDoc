import numpy as np
import fitz
import pytest

from app.parsing import profile_document_fonts, page_probably_has_table, score_header_row
from app.retrieval import calculate_term_coverage, rrf_fusion, apply_intent_boost, VectorIndex, BM25Index
from app.schemas import Chunk


def test_1_font_profiling_modal_size():
    """Unit test 1: Font profiling returns correct modal font size."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Body text line 1", fontsize=10)
    page.insert_text((50, 70), "Body text line 2", fontsize=10)
    page.insert_text((50, 90), "Body text line 3", fontsize=10)
    page.insert_text((50, 120), "HEADING TITLE", fontsize=18)
    
    modal_size = profile_document_fonts(doc, sample_pages=15)
    doc.close()
    assert modal_size == 10.0


def test_2_table_triage_rejects_prose():
    """Unit test 2: Table triage rejects pure prose pages (<2% digits)."""
    doc = fitz.open()
    page = doc.new_page()
    prose_lines = [
        ("The quick brown fox jumps over the lazy dog repeatedly.", 10.0, False, (50, 50, 400, 60)),
        ("This is pure financial narrative commentary without numbers.", 10.0, False, (50, 70, 400, 80))
    ]
    has_table = page_probably_has_table(page, prose_lines)
    doc.close()
    assert has_table is False


def test_3_table_triage_accepts_numerical_grid():
    """Unit test 3: Table triage accepts page with high digit ratio."""
    doc = fitz.open()
    page = doc.new_page()
    numeric_lines = [
        ("Revenue FY2024: 45000000 FY2025: 52000000 Profit: 12000000", 10.0, False, (50, 50, 400, 60)),
        ("Q1: 1200 Q2: 1450 Q3: 1600 Q4: 1800 Tax: 25% Ebitda: 35%", 10.0, False, (50, 70, 400, 80))
    ]
    has_table = page_probably_has_table(page, numeric_lines)
    doc.close()
    assert has_table is True


def test_4_blob_storage_size_reduction():
    """Unit test 4: BLOB vector storage is significantly smaller than JSON representation."""
    import json
    vec = np.random.randn(384).astype(np.float32)
    blob_bytes = vec.tobytes()
    json_bytes = json.dumps({"chunk_id": "c1"*10, "vector": vec.tolist()}).encode('utf-8')
    
    assert len(blob_bytes) == 1536  # Exactly 384 * 4 bytes
    assert len(json_bytes) > 5000   # Over 5KB as JSON
    ratio = len(json_bytes) / len(blob_bytes)
    assert ratio >= 3.0  # BLOB is much smaller than JSON


def test_5_rrf_formula_calculation():
    """Unit test 5: Verify RRF score calculation formula with k=60."""
    dense = [("chunk_a", 0.9), ("chunk_b", 0.8)]
    sparse = [("chunk_b", 12.0), ("chunk_a", 10.0)]
    
    expected_score = (1.0 / 61.0) + (1.0 / 62.0)
    fusion = rrf_fusion(dense, sparse, k=60)
    
    assert pytest.approx(fusion[0][1], rel=1e-5) == expected_score


def test_6_term_coverage_calculation():
    """Unit test 6: Verify term coverage calculation for 0.6 threshold."""
    query = "What is the net profit margin for Q3?"
    chunk_full = "The net profit margin for Q3 reached 18.5 percent."
    chunk_partial = "The document discusses financial results."
    
    cov_full = calculate_term_coverage(query, chunk_full)
    cov_partial = calculate_term_coverage(query, chunk_partial)
    
    assert cov_full >= 0.80
    assert cov_partial < 0.60


def test_7_intent_boost_table_boost():
    """Unit test 7: Intent boost elevates table chunk ranks on numeric queries."""
    c_text = Chunk("1", "doc", "f.pdf", 1, "Sec", "text", "text", "context")
    c_table = Chunk("2", "doc", "f.pdf", 1, "Sec", "table", "Revenue 5000", "context")
    chunk_map = {"1": c_text, "2": c_table}
    
    rrf_initial = [("1", 0.03), ("2", 0.02)]
    boosted = apply_intent_boost("What is the revenue table for FY2024?", rrf_initial, chunk_map)
    
    assert boosted[0][0] == "2"  # Table chunk boosted to rank 1


def test_8_header_row_scoring():
    """Unit test 8: Score header row selects dense concise row over sparse row."""
    dense_row = ["Quarter", "Revenue", "EBITDA", "Net Profit"]
    sparse_row = ["", "", "Unrelated Notes", ""]
    
    score_dense = score_header_row(dense_row)
    score_sparse = score_header_row(sparse_row)
    
    assert score_dense > score_sparse


def test_21_bm25_index_tokenization_and_score():
    """Unit test 21: Custom BM25 index correctly computes term scores."""
    bm25 = BM25Index()
    c1 = Chunk("c1", "doc", "f.pdf", 1, "Sec", "text", "EBITDA revenue growth", "context")
    c2 = Chunk("c2", "doc", "f.pdf", 2, "Sec", "text", "Employee background story", "context")
    
    bm25.add_chunks([c1, c2])
    res = bm25.search("revenue growth", top_k=5)
    
    assert len(res) == 1
    assert res[0][0] == "c1"


def test_22_vector_index_add_and_search():
    """Unit test 22: VectorIndex correctly searches matrix."""
    v_idx = VectorIndex(dim=384)
    v1 = np.ones(384, dtype=np.float32) / np.sqrt(384)
    v2 = np.zeros(384, dtype=np.float32)
    v2[0] = 1.0
    
    v_idx.add(["c1", "c2"], np.vstack([v1, v2]))
    res = v_idx.search(v1, top_k=2)
    
    assert len(res) == 2
    assert res[0][0] == "c1"


def test_31_config_and_model_settings():
    """Unit test 31: Config correctly defines model names, timeouts, and key aliases."""
    from app.config import settings
    assert settings.OLLAMA_MODEL == "hf.co/armand0e/Qwen3.5-9B-Opus-Agent-GGUF:Q5_K_M"
    assert settings.OLLAMA_TIMEOUT >= 10.0
    assert settings.GEMINI_MODEL == "gemini-flash-latest"
    assert settings.GROQ_MODEL == "llama-3.3-70b-versatile"
    assert settings.OPENAI_MODEL == "gpt-4o-mini"
    assert settings.GROQ_API_KEY != ""


def test_32_circuit_breaker_reset():
    """Unit test 32: ProviderCircuitBreaker reset() restores CLOSED state."""
    from app.resilience.circuit_breaker import ProviderCircuitBreaker
    cb = ProviderCircuitBreaker(failure_threshold=3)
    for _ in range(3):
        cb.record_failure("gemini")
    assert cb.can_call("gemini") is False
    assert cb.providers["gemini"]["state"] == "OPEN"

    cb.reset("gemini")
    assert cb.can_call("gemini") is True
    assert cb.providers["gemini"]["state"] == "CLOSED"
    assert len(cb.providers["gemini"]["failures"]) == 0

    # Test reset all
    for _ in range(3):
        cb.record_failure("groq")
        cb.record_failure("ollama")
    assert cb.can_call("groq") is False
    assert cb.can_call("ollama") is False

    cb.reset()
    assert cb.can_call("groq") is True
    assert cb.can_call("ollama") is True


def test_33_llm_provider_client_models():
    """Unit test 33: MultiProviderLLMClient returns configured model names."""
    from app.llm import MultiProviderLLMClient
    from app.config import settings
    client = MultiProviderLLMClient()

    _, m_gem, p_gem = client._get_provider_client("gemini")
    assert m_gem == settings.GEMINI_MODEL
    assert p_gem == "gemini"

    _, m_groq, p_groq = client._get_provider_client("groq")
    assert m_groq == settings.GROQ_MODEL
    assert p_groq == "groq"

    _, m_ollama, p_ollama = client._get_provider_client("ollama")
    assert m_ollama == settings.OLLAMA_MODEL
    assert p_ollama == "ollama"

