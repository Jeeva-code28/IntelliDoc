"""
Intent Router for Project NPN.

WHY THIS FILE EXISTS
--------------------
The original system had exactly one behaviour: treat every incoming message as a
question about the uploaded documents. Anything that was not a document question
fell through into the relevance gate, found no supporting passage, and was
answered with "I cannot answer this based on the provided document."

That made the product feel broken for ordinary English input:

    "hi!"                  -> refused (the old check was an exact match on "hi")
    "who are you?"         -> refused
    "what can you do?"     -> refused
    "thanks, that helped"  -> refused
    "explain what EBITDA means" -> refused, even though it is answerable

The fix is not model training. It is routing: decide what KIND of message this
is, then handle each kind with the appropriate strategy. Retrieval is only one
of several valid strategies.

DESIGN
------
Two-tier classification, cheapest first:

  Tier 1 (rules, ~0.1ms, free)  -> catches greetings, thanks, farewells and
                                   meta questions with high precision.
  Tier 2 (one small LLM call)   -> only for genuinely ambiguous input, and only
                                   when a cheap heuristic cannot decide.

Tier 1 handles the overwhelming majority of non-document traffic, so the LLM
call is rare and the added latency is close to zero in practice.
"""

import re
from enum import Enum
from typing import Optional, List, Tuple


class Intent(str, Enum):
    """The kinds of message the system knows how to handle."""

    GREETING = "greeting"            # "hi", "good morning", "hey there"
    SMALLTALK = "smalltalk"          # "thanks", "bye", "cool", "how are you"
    META = "meta"                    # "who are you", "what can you do"
    GENERAL_KNOWLEDGE = "general"    # "what does EBITDA mean" - answerable without the docs
    DOCUMENT_QA = "document_qa"      # the core case: ask the documents
    INJECTION = "injection"          # prompt-injection / jailbreak attempt


# ---------------------------------------------------------------------------
# Tier 1: rule patterns
# ---------------------------------------------------------------------------
# Anchored with \b word boundaries and applied to punctuation-stripped,
# lowercased text, so "Hi!!", "  hello.", and "HEY THERE" all match. This is
# the specific weakness of the original exact-string-match approach.

_GREETING_PATTERNS = [
    r"^(hi|hey|hello|yo|hiya|howdy|sup)\b",
    r"^good\s+(morning|afternoon|evening|day)\b",
    r"^(namaste|vanakkam|hola)\b",
    r"^greetings\b",
]

_SMALLTALK_PATTERNS = [
    r"^(thanks|thank you|thx|ty|cheers)\b",
    r"^(bye|goodbye|see you|later|good night)\b",
    # Deliberately no trailing $ here: "ok cool", "okay thanks", "great, got it"
    # are still bare acknowledgements even with a second word tacked on. This
    # rule only runs inside the word_count<=5 branch in classify_rules(), so
    # it cannot swallow a real question like "cool, but what was revenue" -
    # that's 6 words and skips this tier entirely.
    r"^(ok|okay|cool|nice|great|awesome|perfect|got it|understood|sure)\b",
    r"^how'?s?\s+(it\s+going|things|life|everything|you\s+doing)\b",
    r"^how are you\b",
    r"^(what'?s up|whats up)\b",
    r"^(sorry|my bad)\b",
    r"^(yes|yeah|yep|no|nope|nah)\b$",
]

_META_PATTERNS = [
    r"\b(who|what)\s+(are|r)\s+you\b",
    r"\bwhat\s+(can|do)\s+you\s+(do|help|answer)\b",
    r"\bwhat\s+is\s+your\s+(name|purpose|job)\b",
    r"\bhow\s+do\s+you\s+work\b",
    r"\bwhat\s+(kind|type)s?\s+of\s+(file|document|format)s?\s+",
    r"\bare\s+you\s+(an?\s+)?(ai|bot|human|chatgpt|gpt|llm)\b",
    r"\bwho\s+(made|built|created)\s+you\b",
    r"\bwhat\s+model\s+(are|do)\s+you\b",
    r"\bhelp\b$",
]

# Kept deliberately narrow. These are attack signatures, not merely unusual
# phrasing, so a normal user question will not trip them.
_INJECTION_PATTERNS = [
    r"\bignore\s+(all\s+)?(previous|prior|above|the)\s+(instruction|prompt|rule)",
    r"\b(reveal|show|print|repeat|output)\s+(me\s+)?(your|the)\s+system\s+prompt",
    r"\byou\s+are\s+now\b.*\b(dan|jailbroken|unrestricted|developer\s+mode)\b",
    r"\b(admin|god|developer|sudo)\s+mode\b",
    r"\bdisregard\s+(your|all|the)\s+(rule|instruction|guideline)",
    r"\bpretend\s+(you\s+)?(have\s+no|there\s+are\s+no)\s+(rule|restriction|filter)",
]

# Signals that a question is about the user's own documents rather than the
# world in general. Presence of these pushes toward DOCUMENT_QA.
_DOCUMENT_DEICTIC = [
    r"\b(this|the|my|our|attached|uploaded|these)\s+"
    r"(document|doc|file|pdf|report|statement|sheet|paper|contract|invoice|resume|cv)\b",
    r"\bin\s+the\s+(document|report|pdf|file|attachment)\b",
    r"\baccording\s+to\s+the\b",
    r"\b(page|section|table|figure|appendix|exhibit)\s*\d+\b",
    r"\bwhat\s+does\s+(it|the\s+\w+)\s+say\b",
    r"\bsummar(ise|ize|y)\b",
]

# Generic definitional phrasing with no reference to the user's documents.
# "what does EBITDA mean" is answerable from world knowledge.
_DEFINITIONAL = [
    r"^what\s+(is|are|does|do)\s+(a|an|the)?\s*[\w\s\-]{1,40}\s*(mean|stand\s+for)\??$",
    r"^(define|explain|describe)\s+(the\s+(term|concept|meaning)\s+of\s+)?[\w\s\-]{1,40}\??$",
    r"^what\s+(is|are)\s+(a|an|the)?\s*[\w\s\-]{1,40}\??$",
]


def _normalise(text: str) -> str:
    """Lowercase, collapse whitespace, strip surrounding punctuation.

    This single step is what makes "Hi!!!" and "  HELLO. " behave like "hi",
    which the original exact-match implementation could not do.
    """
    t = text.strip().lower()
    t = re.sub(r"\s+", " ", t)
    return t.strip(" \t\n!?.,;:\"'")


def _matches_any(text: str, patterns: List[str]) -> bool:
    return any(re.search(p, text) for p in patterns)


_WH_STARTERS = (
    "what", "how", "when", "where", "why", "which", "who",
    "can", "could", "would", "will", "does", "do", "is", "are",
    "tell", "show", "give", "explain", "summar", "list", "find",
)


def _is_substantive(remainder: str) -> bool:
    """After stripping a matched greeting/smalltalk prefix, decide whether
    what's LEFT is a real information request rather than trailing filler.

    This is what correctly separates "ok cool" (pure smalltalk, nothing left)
    from "cool, what was the revenue" (an acknowledgement bolted onto a real
    question - must route to DOCUMENT_QA, not be swallowed as smalltalk).
    """
    remainder = remainder.strip(" ,.!?;:")
    if not remainder:
        return False
    if "?" in remainder:
        return True
    words = remainder.split()
    if len(words) >= 3:
        return True
    return words[0].startswith(_WH_STARTERS) if words else False


def _match_prefix(text: str, patterns: List[str]) -> Optional[re.Match]:
    """Return the Match for the first pattern that matches at the START of
    text, or None. Unlike _matches_any, this is used when we need to know
    WHERE the match ends, to inspect what comes after it."""
    for p in patterns:
        m = re.match(p, text)
        if m:
            return m
    return None


def classify_rules(query: str) -> Tuple[Optional[Intent], float, str]:
    """Tier 1 rule-based classification.

    Returns (intent, confidence, reason). Intent is None when the rules cannot
    decide, in which case the caller may escalate to the LLM tier.
    """
    q = _normalise(query)

    if not q:
        return Intent.SMALLTALK, 1.0, "empty input"

    # Injection first: it must win regardless of any other signal.
    if _matches_any(q, _INJECTION_PATTERNS):
        return Intent.INJECTION, 0.99, "matched injection signature"

    # Greeting / smalltalk prefix check. Rather than gating on overall message
    # length (which misfires both ways - "ok cool" is short but real
    # questions can be short too, e.g. "cool, what was the revenue" is only
    # 5 words), we match the greeting/smalltalk phrase itself and then look
    # at what's left AFTER it. Nothing left (or only filler) -> genuinely
    # conversational. A real question left over -> fall through and let the
    # remaining rules (META / DOCUMENT_DEICTIC / DEFINITIONAL) classify it.
    greeting_match = _match_prefix(q, _GREETING_PATTERNS)
    if greeting_match:
        remainder = q[greeting_match.end():]
        if not _is_substantive(remainder):
            return Intent.GREETING, 0.95, "greeting with no substantive follow-up"
        q = remainder.strip(" ,.!?;:")  # reclassify only the leftover question

    smalltalk_match = _match_prefix(q, _SMALLTALK_PATTERNS)
    if smalltalk_match:
        remainder = q[smalltalk_match.end():]
        if not _is_substantive(remainder):
            return Intent.SMALLTALK, 0.92, "smalltalk with no substantive follow-up"
        q = remainder.strip(" ,.!?;:")

    if _matches_any(q, _META_PATTERNS):
        return Intent.META, 0.90, "asking about the assistant itself"

    # Explicit reference to the user's documents is a strong DOCUMENT_QA signal.
    if _matches_any(q, _DOCUMENT_DEICTIC):
        return Intent.DOCUMENT_QA, 0.93, "explicit reference to the documents"

    # If we stripped a conversational prefix above and what's left is a real
    # question, that's DOCUMENT_QA by default (the safe default - see route()).
    if (greeting_match or smalltalk_match) and _is_substantive(q):
        return Intent.DOCUMENT_QA, 0.75, "conversational prefix followed by a real question"

    # Bare definitional questions with no document reference.
    if _matches_any(q, _DEFINITIONAL) and len(q.split()) <= 10:
        return Intent.GENERAL_KNOWLEDGE, 0.65, "generic definitional phrasing"

    # Undecided. Let the caller escalate.
    return None, 0.0, "no rule matched"


# ---------------------------------------------------------------------------
# Tier 2: LLM fallback
# ---------------------------------------------------------------------------

_LLM_ROUTER_PROMPT = """You are an intent classifier for a document question-answering assistant.

The user has uploaded business documents (financial reports, product and brand documentation). Classify their message into exactly one category:

- "document_qa": asking for information that would come from their uploaded documents. This is the DEFAULT for any substantive question about facts, figures, people, dates, terms, policies or content.
- "general": a general-knowledge or definitional question answerable from world knowledge, with no reference to their documents (e.g. "what does EBITDA mean").
- "meta": asking about the assistant itself - its identity, capabilities or limits.
- "smalltalk": greetings, thanks, farewells, acknowledgements, or chit-chat with no information request.

When genuinely uncertain, choose "document_qa".

Reply with ONLY the category string and nothing else."""


def classify_with_llm(query: str, llm_client) -> Tuple[Intent, float, str]:
    """Tier 2 classification. Falls back to DOCUMENT_QA on any failure.

    DOCUMENT_QA is the safe default: routing a general question to retrieval
    yields a graceful "not in the documents" response, whereas routing a
    document question to general chat would produce an ungrounded answer -
    the far worse failure for this product.
    """
    try:
        client, model, _ = llm_client._get_provider_client()
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _LLM_ROUTER_PROMPT},
                {"role": "user", "content": query[:500]},
            ],
            temperature=0.0,
            max_tokens=10,
        )
        raw = (resp.choices[0].message.content or "").strip().lower()
        raw = re.sub(r"[^a-z_]", "", raw)

        mapping = {
            "document_qa": Intent.DOCUMENT_QA,
            "general": Intent.GENERAL_KNOWLEDGE,
            "meta": Intent.META,
            "smalltalk": Intent.SMALLTALK,
        }
        if raw in mapping:
            return mapping[raw], 0.85, f"llm classified as {raw}"
        return Intent.DOCUMENT_QA, 0.5, f"unparsed llm output '{raw}', defaulted"
    except Exception as e:
        return Intent.DOCUMENT_QA, 0.5, f"llm router unavailable ({type(e).__name__}), defaulted"


def route(query: str, llm_client=None, has_documents: bool = True) -> Tuple[Intent, float, str]:
    """Main entry point. Classify a user message.

    Args:
        query: the raw user message.
        llm_client: optional MultiProviderLLMClient for tier-2 escalation.
        has_documents: whether this conversation has any indexed documents.
            With no documents, retrieval cannot possibly succeed, so a
            substantive question is better served as general knowledge with a
            clear note that nothing has been uploaded yet.

    Returns:
        (intent, confidence, reason) - reason is logged and surfaced in the
        API response for demo transparency.
    """
    intent, conf, reason = classify_rules(query)

    if intent is None:
        if llm_client is not None:
            intent, conf, reason = classify_with_llm(query, llm_client)
        else:
            intent, conf, reason = Intent.DOCUMENT_QA, 0.5, "no rule matched, defaulted"

    if intent == Intent.DOCUMENT_QA and not has_documents:
        return Intent.GENERAL_KNOWLEDGE, conf, "no documents indexed in this conversation"

    return intent, conf, reason
