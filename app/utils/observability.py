"""Observability: structured logging, OpenTelemetry, and Prometheus metrics."""
from __future__ import annotations

import logging

import structlog
from prometheus_client import Counter, Histogram

# ── Prometheus metrics ────────────────────────────────────────────────────────

leads_ingested = Counter("loce_leads_ingested_total", "Total leads ingested", ["source"])
dedupe_outcomes = Counter(
    "loce_dedupe_outcomes_total", "Dedupe outcomes per NBFC", ["nbfc_id", "outcome"]
)
comm_sends = Counter(
    "loce_comm_sends_total", "Communication sends", ["channel", "partner", "status"]
)
webhook_events = Counter(
    "loce_webhook_events_total", "Webhook events received", ["channel", "partner", "event_type"]
)
request_duration = Histogram(
    "loce_http_request_duration_seconds", "HTTP request duration", ["method", "path", "status"]
)

# Expose a generic meter reference for other modules
meter = None  # Will be replaced with OTEL meter on configure_otel()


# ── Structured logging ────────────────────────────────────────────────────────


def configure_logging(level: str = "INFO") -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )


# ── OpenTelemetry ─────────────────────────────────────────────────────────────


def configure_otel(service_name: str, otlp_endpoint: str) -> None:
    """Configure OpenTelemetry tracing and metrics exporters (best-effort)."""
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import SERVICE_NAME, Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource(attributes={SERVICE_NAME: service_name})
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
    except Exception:
        pass  # Observability is non-critical; app continues without it
