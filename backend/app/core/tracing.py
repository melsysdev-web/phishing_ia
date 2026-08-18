"""Distributed tracing with OpenTelemetry and Jaeger exporter."""

import logging
from typing import Optional

try:
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    TracerProvider = None  # type: ignore

logger = logging.getLogger(__name__)


def init_tracing(
    app,
    jaeger_host: str = "localhost",
    jaeger_port: int = 6831,
    service_name: str = "phishing-api",
    enabled: bool = True,
) -> Optional[object]:
    """
    Initialize OpenTelemetry tracing with Jaeger exporter.

    Traces:
    - HTTP requests (FastAPI)
    - External API calls (requests library)
    - Custom spans for business logic

    Args:
        app: FastAPI application instance
        jaeger_host: Jaeger agent hostname
        jaeger_port: Jaeger agent UDP port
        service_name: Service name for traces
        enabled: Whether to enable tracing (useful for dev/test)

    Returns:
        TracerProvider instance or None if disabled/unavailable

    Example:
        ```python
        from backend.app.core.tracing import init_tracing

        trace_provider = init_tracing(app, service_name="phishing-api")
        ```
    """
    if not enabled:
        logger.info("Tracing disabled")
        return None

    if not OTEL_AVAILABLE:
        logger.warning(
            "OpenTelemetry not installed. Install with: "
            "pip install opentelemetry-api opentelemetry-sdk "
            "opentelemetry-exporter-jaeger opentelemetry-instrumentation-fastapi"
        )
        return None

    try:
        jaeger_exporter = JaegerExporter(
            agent_host_name=jaeger_host,
            agent_port=jaeger_port,
        )

        trace_provider = TracerProvider()
        trace_provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))

        FastAPIInstrumentor.instrument_app(app)
        RequestsInstrumentor().instrument()

        logger.info(f"Tracing initialized: {service_name} → {jaeger_host}:{jaeger_port}")
        return trace_provider

    except Exception as e:
        logger.warning(f"Failed to initialize tracing: {e}. Continuing without tracing.")
        return None
