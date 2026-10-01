import pytest
from app.llm import MultiProviderLLMClient
from app.resilience.circuit_breaker import get_circuit_breaker


def test_chaos_llm_provider_blackout():
    """
    Chaos Experiment 3: Total blackout across all cloud and local LLM API providers.
    Verifies circuit breaker trips OPEN for failing providers and rule-based fallback yields grounded response.
    """
    cb = get_circuit_breaker()
    client = MultiProviderLLMClient()

    # Force 3 consecutive failures for Gemini, Groq, OpenAI, and Ollama
    for _ in range(3):
        cb.record_failure("gemini")
        cb.record_failure("groq")
        cb.record_failure("openai")
        cb.record_failure("ollama")

    assert cb.can_call("gemini") is False
    assert cb.can_call("groq") is False
    assert cb.can_call("openai") is False
    assert cb.can_call("ollama") is False

    # Perform grounded answer generation during blackout
    answer, provider_used = client.generate_grounded_answer(
        query="What is the net revenue for FY2025?",
        formatted_context="Page 1: Net revenue for FY2025 reached Rs. 520 Crore."
    )

    assert answer is not None
    assert len(answer) > 0
    assert "520" in answer or "revenue" in answer.lower()
    assert provider_used == "rule_based_fallback"

    # Reset circuit breaker for subsequent tests
    cb.record_success("gemini")
    cb.record_success("groq")
    cb.record_success("openai")
    cb.record_success("ollama")
