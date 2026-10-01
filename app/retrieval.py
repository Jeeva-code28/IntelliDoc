import re
import math
import numpy as np
from typing import List, Dict, Tuple, Set, Optional, Any
from app.config import settings
from app.schemas import Chunk
from app.vector_store import NumpyVectorStore

VectorIndex = NumpyVectorStore

STOPWORDS: Set[str] = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by", "can",
    "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down",
    "during", "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't", "have", "haven't",
    "having", "he", "he'd", "he'll", "he's", "her", "here", "here's", "hers", "herself", "him", "himself",
    "his", "how", "how's", "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's",
    "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself", "no", "nor", "not", "of", "off",
    "on", "once", "only", "or", "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same",
    "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such", "than", "that",
    "that's", "the", "their", "theirs", "them", "themselves", "then", "there", "there's", "these", "they",
    "they'd", "they'll", "they're", "they've", "this", "those", "through", "to", "too", "under", "until", "up",
    "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were", "weren't", "what", "what's",
    "when", "when's", "where", "where's", "which", "while", "who", "who's", "whom", "why", "why's", "with",
    "won't", "would", "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours", "yourself",
    "yourselves"
}


def calculate_term_coverage(query: str, chunk_text: str) -> float:
    """
    Calculates term coverage: fraction of query non-stopword content terms found in chunk_text.
    Handles alphanumeric codes, timestamps, and modality tokens.
    """
    words = re.findall(r'\b[a-zA-Z0-9_:-]+\b', query.lower())
    content_words = [w for w in words if w not in STOPWORDS and len(w) > 1 and not (w.isdigit() and len(w) == 4)]
    if not content_words:
        return 1.0

    chunk_words_set = set(re.findall(r'\b[a-zA-Z0-9_:-]+\b', chunk_text.lower()))
    matches = sum(1 for w in content_words if w in chunk_words_set)
    return matches / len(content_words)


class BM25Index:
    """
    Custom In-Memory BM25 Index with pre-computed IDF scores at build time.
    Parameters: k1=1.5, b=0.75.
    """

    def __init__(self, k1: float = settings.BM25_K1, b: float = settings.BM25_B):
        self.k1 = k1
        self.b = b
        self.chunk_ids: List[str] = []
        self.doc_tokens: List[List[str]] = []
        self.doc_lengths: List[int] = []
        self.avg_doc_len: float = 0.0
        self.df: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}

    def tokenize(self, text: str) -> List[str]:
        return [w for w in re.findall(r'\b[a-zA-Z0-9_:-]+\b', text.lower()) if w not in STOPWORDS]

    def add_chunks(self, chunks: List[Chunk]):
        for c in chunks:
            self.chunk_ids.append(c.id)
            tokens = self.tokenize(c.text)
            self.doc_tokens.append(tokens)
            self.doc_lengths.append(len(tokens))

            unique_terms = set(tokens)
            for t in unique_terms:
                self.df[t] = self.df.get(t, 0) + 1

        total_docs = len(self.chunk_ids)
        if total_docs > 0:
            self.avg_doc_len = sum(self.doc_lengths) / total_docs
            # Pre-compute IDF scores at index build time (Hot-path optimization)
            for term, freq in self.df.items():
                self.idf[term] = math.log((total_docs - freq + 0.5) / (freq + 0.5) + 1.0)

    def clear(self):
        self.chunk_ids.clear()
        self.doc_tokens.clear()
        self.doc_lengths.clear()
        self.avg_doc_len = 0.0
        self.df.clear()
        self.idf.clear()

    def search(self, query: str, top_k: int = settings.TOP_K_SPARSE) -> List[Tuple[str, float]]:
        total_docs = len(self.chunk_ids)
        if total_docs == 0:
            return []

        q_tokens = self.tokenize(query)
        if not q_tokens:
            return []

        scores = np.zeros(total_docs, dtype=np.float32)

        for q_term in q_tokens:
            if q_term not in self.idf:
                continue
            idf_val = self.idf[q_term]
            for doc_idx, tokens in enumerate(self.doc_tokens):
                tf = tokens.count(q_term)
                if tf == 0:
                    continue
                doc_len = self.doc_lengths[doc_idx]
                numerator = tf * (self.k1 + 1.0)
                denominator = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / self.avg_doc_len))
                scores[doc_idx] += idf_val * (numerator / denominator)

        if total_docs <= top_k:
            top_indices = np.argsort(scores)[::-1]
        else:
            partitioned = np.argpartition(scores, -top_k)[-top_k:]
            top_indices = partitioned[np.argsort(scores[partitioned])[::-1]]

        results = []
        for idx in top_indices:
            if scores[idx] > 0:
                results.append((self.chunk_ids[idx], float(scores[idx])))
        return results


def rrf_fusion(
    dense_results: List[Tuple[str, float]],
    sparse_results: List[Tuple[str, float]],
    k: int = settings.RRF_K
) -> List[Tuple[str, float]]:
    """
    Reciprocal Rank Fusion (RRF) with constant k=60.
    Combines dense and sparse ranking positions without magnitude bias.
    """
    scores: Dict[str, float] = {}

    for rank, (chunk_id, _) in enumerate(dense_results, start=1):
        scores[chunk_id] = scores.get(chunk_id, 0.0) + (1.0 / (k + rank))

    for rank, (chunk_id, _) in enumerate(sparse_results, start=1):
        scores[chunk_id] = scores.get(chunk_id, 0.0) + (1.0 / (k + rank))

    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return sorted_scores


def apply_intent_boost(
    query: str,
    rrf_rankings: List[Tuple[str, float]],
    chunk_map: Dict[str, Chunk]
) -> List[Tuple[str, float]]:
    """
    Multi-modal Intent Boosting Engine.
    Dynamically adjusts ranking weights based on user query intent for:
    - Tables / Numeric data (revenue, margins, tables, balances)
    - Figures / Images / Diagrams (charts, diagrams, schematics, photos)
    - Video (clips, scenes, keyframes, motion, timestamps)
    - Audio (recordings, speech, transcripts, spoken remarks, calls)
    - Attachments (spreadsheets, archives, files)
    """
    query_lower = query.lower()

    numeric_kws = [
        "revenue", "profit", "ebitda", "table", "margin", "quarter", "quarterly",
        "fy20", "fy21", "fy22", "fy23", "fy24", "fy25", "%", "lakhs",
        "crores", "balance", "sheet", "cash flow", "expenses", "operating income", "net income", "$"
    ]
    visual_kws = [
        "chart", "figure", "image", "diagram", "graph", "plot", "picture",
        "photo", "schematic", "visual", "flowchart", "bar chart", "pie chart", "trend"
    ]
    video_kws = [
        "video", "clip", "keyframe", "frame", "scene", "motion", "animation",
        "watch", "presentation", "timeline", "seconds", "duration", "slide"
    ]
    audio_kws = [
        "audio", "recording", "transcript", "spoken", "speaker", "voice",
        "call", "listen", "said", "discussed", "remarks", "earnings call", "guidance", "cfo", "ceo"
    ]
    attachment_kws = [
        "attachment", "archive", "zip", "attached", "quarantine", "csv", "tsv", "file"
    ]

    is_numeric_query = any(kw in query_lower for kw in numeric_kws)
    is_visual_query = any(kw in query_lower for kw in visual_kws)
    is_video_query = any(kw in query_lower for kw in video_kws)
    is_audio_query = any(kw in query_lower for kw in audio_kws)
    is_attachment_query = any(kw in query_lower for kw in attachment_kws)

    if not (is_numeric_query or is_visual_query or is_video_query or is_audio_query or is_attachment_query):
        return rrf_rankings

    boosted_scores: Dict[str, float] = {}
    for rank, (cid, score) in enumerate(rrf_rankings, start=1):
        chunk = chunk_map.get(cid)
        effective_score = score

        if chunk:
            c_type = chunk.content_type
            if is_numeric_query and c_type == "table":
                effective_score += (3.5 / (settings.RRF_K + rank))
            if is_visual_query and c_type in ["figure", "image"]:
                effective_score += (3.5 / (settings.RRF_K + rank))
            if is_video_query and c_type == "video":
                effective_score += (4.0 / (settings.RRF_K + rank))
            if is_audio_query and c_type == "audio":
                effective_score += (4.0 / (settings.RRF_K + rank))
            if is_attachment_query and c_type in ["attachment", "attachment_quarantined", "table", "video", "audio", "image"]:
                effective_score += (2.5 / (settings.RRF_K + rank))

        boosted_scores[cid] = effective_score

    sorted_boosted = sorted(boosted_scores.items(), key=lambda x: x[1], reverse=True)
    return sorted_boosted
