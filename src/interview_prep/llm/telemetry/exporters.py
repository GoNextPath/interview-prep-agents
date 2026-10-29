"""Application-owned OpenTelemetry SDK/exporter setup; disabled by default."""

import sys

from interview_prep.llm.contracts import ConfigurationError


def configure_telemetry(exporter: str):
    """Application entry point only. Embedding apps should configure their own SDK instead."""
    if exporter == "off":
        return None
    if exporter not in {"console", "otlp"}:
        raise ConfigurationError("INTERVIEW_PREP_TELEMETRY must be off, console, or otlp")
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import (
            BatchSpanProcessor,
            ConsoleSpanExporter,
            SimpleSpanProcessor,
        )

        if exporter == "otlp":
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    except ImportError:
        raise ConfigurationError('Telemetry setup requires: pip install -e ".[telemetry]"') from None
    if not isinstance(trace.get_tracer_provider(), trace.ProxyTracerProvider):
        raise ConfigurationError("A tracer provider is already configured; use the existing application SDK")
    provider = TracerProvider(resource=Resource.create({"service.name": "interview-prep-agents"}))
    if exporter == "console":
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter(out=sys.stderr)))
    else:
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)
    return provider
