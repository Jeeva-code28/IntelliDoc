import re
import pytest
from app.rag import get_rag_service
from app.llm import get_llm_client
from app.multimedia import get_multimedia_processor
from app.schemas import QueryRequest, Chunk, CitationSource, QueryResponse


def test_caption_image_no_fabricated_metrics():
    """Verify that figure captioning never invents EBITDA margins or quarterly revenue."""
    processor = get_multimedia_processor()
    caption = processor.caption_image("page_8_fig_3.jpeg", "Cash and Investments")
    
    assert "EBITDA" not in caption
    assert "quarterly revenue" not in caption
    assert "expenditure distribution" not in caption
    assert "Cash and Investments" in caption
    assert "uninterpreted" in caption


def test_rule_based_fallback_answer_structure():
    """Verify that the fallback synthesizer generates polished Markdown and never dumps raw chunks."""
    llm_client = get_llm_client()

    formatted_context = (
        "SOURCE [S1] (basic-understanding-of-a-companys-financials.pdf, type: text, p.8, Section: Cash and Investments):\n"
        "Page 8 | Section: Cash and Investments\n\n"
        "A company will hold external investments for two reasons: Excess cash; Accumulating cash to make a large purchase.\n"
        "• Investments in equity or debt instruments to be held for capital gain and/or income\n"
        "• Investment in subsidiaries, associates and joint ventures\n\n"
        "SOURCE [S2] (basic-understanding-of-a-companys-financials.pdf, type: text, p.8, Section: Cash and Investments):\n"
        "Page 8 | Section: Cash and Investments\n\n"
        "Internal investments: Short term (less than year) and Long term (more than year)."
    )

    query = "Tell me about cash and investments."
    ans = llm_client._rule_based_fallback_answer(query, formatted_context)

    # Must NOT contain raw retrieval / debug artifacts
    assert "Based on the ingested document analysis:" not in ans
    assert "[SOURCE [S1]" not in ans
    assert "[SOURCE S1]" not in ans
    assert "Document:" not in ans
    assert "p.8, Section:" not in ans
    
    # Must contain clear structure
    assert ans.startswith("### ") or "### Cash and Investments" in ans
    assert "According to the selected document" in ans
    assert "- **" in ans or "- " in ans
    assert "[S1]" in ans or "[S2]" in ans
    assert "**Source:**" in ans


def test_rule_based_fallback_answer_insufficient_evidence():
    """Verify that empty or irrelevant context produces standard refusal."""
    llm_client = get_llm_client()
    ans = llm_client._rule_based_fallback_answer("Who is the president?", "")
    assert "cannot answer" in ans.lower()


def test_citation_source_schema_contract():
    """Verify that CitationSource supports document_name, section_heading, and clean excerpt."""
    citation = CitationSource(
        chunk_id="chunk-123",
        document_id="doc-456",
        document_name="annual_report.pdf",
        filename="12345678-1234-1234-1234-123456789abc_annual_report.pdf",
        page_number=8,
        section="Cash and Investments",
        section_heading="Cash and Investments",
        content_type="text",
        snippet="A company will hold external investments for two reasons.",
        excerpt="A company will hold external investments for two reasons.",
        score=0.95
    )

    assert citation.document_name == "annual_report.pdf"
    assert citation.section_heading == "Cash and Investments"
    assert citation.excerpt == "A company will hold external investments for two reasons."
    assert not citation.document_name.startswith("12345678-")


def test_query_response_schema_contract():
    """Verify QueryResponse status and evidence_sufficient fields."""
    resp = QueryResponse(
        status="answered",
        answer="Companies hold cash for excess reserves and capital purchases.",
        citations=[],
        evidence_sufficient=True,
        latency_ms=120.0,
        retrieval_latency_ms=25.0,
        conversation_id="conv-1"
    )

    assert resp.status == "answered"
    assert resp.evidence_sufficient is True

    refusal_resp = QueryResponse(
        status="refused",
        answer="I cannot answer this based on the provided document.",
        citations=[],
        evidence_sufficient=False,
        latency_ms=50.0,
        retrieval_latency_ms=15.0,
        conversation_id="conv-1"
    )

    assert refusal_resp.status == "refused"
    assert refusal_resp.evidence_sufficient is False


def test_figure_chunk_metadata_unverified_flag():
    """Verify that figure chunks have description_verified=False and truthful description."""
    c = Chunk(
        id="c-fig-1",
        document_id="doc-1",
        filename="pwc.pdf",
        page_number=8,
        section="Cash and Investments",
        content_type="figure",
        text="[Figure] Page 8 under section 'Cash and Investments': Embedded image asset page_8_fig_3.jpeg.",
        context_text="Figure: page_8_fig_3.jpeg on Page 8 under section 'Cash and Investments'. (Image asset preserved; visual content uninterpreted).",
        metadata={"description_verified": False}
    )

    assert c.metadata.get("description_verified") is False
    assert "EBITDA" not in c.text
    assert "revenue" not in c.text.lower()
