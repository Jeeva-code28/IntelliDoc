import pytest
from app.llm import MultiProviderLLMClient
from app.resilience.circuit_breaker import get_circuit_breaker


def test_chaos_llm_provider_blackout():
    """
    Chaos Experiment 3: Total blackout across all cloud LLM API providers.
    Verifies circuit breaker trips OPEN for failing providers and local fallback yields grounded response.
    """
    cb = get_circuit_breaker()
    client = MultiProviderLLMClient()

    # Force 3 consecutive failures for Gemini, Groq, and OpenAI
    for _ in range(3):
        cb.record_failure("gemini")
        cb.record_failure("groq")
        cb.record_failure("openai")

    assert cb.can_call("gemini") is False
    assert cb.can_call("groq") is False
    assert cb.can_call("openai") is False

    # Perform grounded answer generation during blackout
    answer, provider_used = client.generate_grounded_answer(
        query="What is the net revenue for FY2025?",
        formatted_context="Page 1: Net revenue for FY2025 reached Rs. 520 Crore."
    )

    assert answer is not None
    assert len(answer) > 0
    assert "520" in answer or "revenue" in answer.lower()
