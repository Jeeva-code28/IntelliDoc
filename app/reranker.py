"""
Cross-encoder reranker for Project NPN.

WHY THIS EXISTS
---------------
Dense (embedding) search scores the query and each chunk INDEPENDENTLY, then
compares the two resulting vectors. That is fast (one matrix multiply) but
lossy: the model never actually reads the query and the candidate passage
side by side.

A cross-encoder reads (query, passage) as a SINGLE input and outputs one
relevance score directly. It is meaningfully more accurate than comparing
separate embeddings, but too slow to run over every chunk in the store. The
standard, and correct, pattern is:

    dense + BM25 + RRF   ->  cheap first pass, ~20-30 plausible candidates
    cross-encoder rerank ->  expensive but accurate, re-scores just those 20-30

This module implements that second stage, and is used for two things in
rag.py: (1) picking the final top-k chunks to hand the LLM, and (2) as the
primary signal for the relevance gate, replacing the old literal-keyword
veto (see NPN_HACKATHON_BRIEF.md, Bug #2).

OFFLINE / FIRST-RUN SAFETY
---------------------------
The cross-encoder model (~280MB) must be downloaded once from HuggingFace
before first use. On a machine with no internet access at demo time, or if
the model was never pre-downloaded, this module logs ONE warning and every
subsequent call transparently falls back to the input order unchanged
(i.e. the RRF + intent-boost ranking) rather than crashing the query.

>>> Run `python -m app.reranker` once, on a machine with internet, well
>>> before Thursday, to pre-download and warm the model. See the bottom
>>> of this file.
"""

from typing import List, Tuple, Optional
from app.schemas import Chunk
from app.observability.logging import logger

_reranker_model = None
_reranker_unavailable = False
_warned = False

RERANKER_MODEL_NAME = "BAAI/bge-reranker-base"


def _get_reranker():
    """Lazily load and cache the cross-encoder. Returns None (and flips a
    sticky flag so we don't retry every request) if it cannot be loaded."""
    global _reranker_model, _reranker_unavailable, _warned

    if _reranker_unavailable:
        return None
    if _reranker_model is not None:
        return _reranker_model

    try:
        from sentence_transformers import CrossEncoder
        _reranker_model = CrossEncoder(RERANKER_MODEL_NAME)
        logger.info("reranker_loaded", model=RERANKER_MODEL_NAME)
        return _reranker_model
    except Exception as e:
        _reranker_unavailable = True
        if not _warned:
            logger.warning(
                "reranker_unavailable_falling_back_to_rrf_order",
                model=RERANKER_MODEL_NAME,
                error=str(e),
            )
            _warned = True
        return None


def is_reranker_available() -> bool:
    """Whether the cross-encoder is loaded and usable. Check this before
    trusting RELEVANCE_RERANK_THRESHOLD-based gating in rag.py."""
    return _get_reranker() is not None


def rerank(query: str, chunks: List[Chunk], top_k: int = 6) -> List[Tuple[Chunk, float]]:
    """Re-score (query, chunk) pairs with the cross-encoder.

    Returns up to top_k (chunk, score) pairs, sorted by score descending.

    If the reranker is unavailable, returns the FIRST top_k input chunks
    unchanged with a score of 0.0 each - the caller (rag.py) already handed
    them in RRF + intent-boost order, so this degrades gracefully rather
    than failing.
    """
    if not chunks:
        return []

    model = _get_reranker()
    if model is None:
        return [(c, 0.0) for c in chunks[:top_k]]

    # context_text (not text) because it's the richer, LLM-facing rendering -
    # markdown tables etc. Truncated defensively; cross-encoders have their
    # own max sequence length and silently truncate anyway.
    pairs = [(query, c.context_text[:1000]) for c in chunks]
    scores = model.predict(pairs)
    ranked = sorted(zip(chunks, scores), key=lambda x: -float(x[1]))
    return [(c, float(s)) for c, s in ranked[:top_k]]


if __name__ == "__main__":
    # Pre-download / warm-up utility. Run this once, on a machine with
    # internet, before the hackathon: `python -m app.reranker`
    print(f"Downloading and loading {RERANKER_MODEL_NAME} ...")
    ok = is_reranker_available()
    if ok:
        print("Reranker ready. Model is now cached locally for offline use.")
        test_scores = rerank(
            "what was quarterly revenue",
            [
                Chunk(
                    id="1", document_id="d", filename="f", page_number=1,
                    section=None, content_type="text",
                    text="Revenue for the quarter was strong.",
                    context_text="Revenue for the quarter was strong.",
                ),
                Chunk(
                    id="2", document_id="d", filename="f", page_number=1,
                    section=None, content_type="text",
                    text="The cafeteria menu changed on Monday.",
                    context_text="The cafeteria menu changed on Monday.",
                ),
            ],
            top_k=2,
        )
        for c, s in test_scores:
            print(f"  score={s:.3f}  text={c.text[:50]!r}")
    else:
        print("Reranker could NOT be loaded. Check internet access and try again.")
