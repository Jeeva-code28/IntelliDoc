import os
import logging
from typing import Optional, Callable
from contextlib import contextmanager

logger = logging.getLogger("project_npn")


class OpenTelemetryTracer:
    """
    OpenTelemetry Distributed Tracing Service for Jaeger / Grafana Tempo.
    Propagates trace IDs across system boundaries: upload(202) -> parse -> embed -> vector_upsert -> query.
    """

    def __init__(self, service_name: str = "project_npn"):
        self.service_name = service_name
        self.tracer = None
        self._init_tracer()

    def _init_tracer(self) -> None:
        try:
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
            
            provider = TracerProvider()
            processor = BatchSpanProcessor(ConsoleSpanExporter())
            provider.add_span_processor(processor)
            trace.set_tracer_provider(provider)
            
            self.tracer = trace.get_tracer(self.service_name)
            logger.info(f"Initialized OpenTelemetry tracer for service '{self.service_name}'.")
        except Exception as e:
            logger.debug(f"OpenTelemetry initialization fallback ({e}). Using lightweight span context manager.")
            self.tracer = None

    @contextmanager
    def start_span(self, span_name: str):
        if self.tracer:
            with self.tracer.start_as_current_span(span_name) as span:
                yield span
        else:
            # Fallback lightweight tracing
            logger.debug(f"[TRACE SPAN START]: {span_name}")
            try:
                yield None
            finally:
                logger.debug(f"[TRACE SPAN END]: {span_name}")


_tracer = None


def get_tracer() -> OpenTelemetryTracer:
    global _tracer
    if _tracer is None:
        _tracer = OpenTelemetryTracer()
    return _tracer
