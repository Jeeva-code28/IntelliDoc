import logging
from typing import Tuple
import structlog
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

# Configure structlog
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger("project_npn")

# Prometheus Metrics Definitions
INGESTION_DURATION = Histogram(
    "npn_ingestion_duration_seconds",
    "Time spent ingesting PDF document in seconds",
    buckets=[1.0, 5.0, 10.0, 15.0, 20.0, 30.0, 60.0]
)

QUERY_LATENCY = Histogram(
    "npn_query_latency_seconds",
    "Latency breakdown of query pipeline in seconds",
    ["stage"],
    buckets=[0.005, 0.010, 0.025, 0.035, 0.050, 0.066, 0.100, 0.500, 1.0, 2.0]
)

LLM_FALLBACK_COUNT = Counter(
    "npn_llm_fallback_total",
    "Total count of LLM provider failover events",
    ["from_provider", "to_provider"]
)


def log_ingestion_complete(doc_id: str, duration_ms: float, page_count: int, table_count: int, chunk_count: int):
    INGESTION_DURATION.observe(duration_ms / 1000.0)
    logger.info(
        "ingestion_complete",
        document_id=doc_id,
        duration_ms=round(duration_ms, 2),
        page_count=page_count,
        table_count=table_count,
        chunk_count=chunk_count
    )


def log_query_served(query: str, latency_ms: float, retrieval_latency_ms: float, chunks_retrieved: int, provider_used: str):
    QUERY_LATENCY.labels(stage="retrieval").observe(retrieval_latency_ms / 1000.0)
    QUERY_LATENCY.labels(stage="total").observe(latency_ms / 1000.0)
    logger.info(
        "query_served",
        query_snippet=query[:50],
        total_latency_ms=round(latency_ms, 2),
        retrieval_latency_ms=round(retrieval_latency_ms, 2),
        chunks_retrieved=chunks_retrieved,
        provider_used=provider_used
    )


def get_prometheus_metrics() -> Tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST
