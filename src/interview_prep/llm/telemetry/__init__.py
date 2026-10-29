"""Public telemetry exports; importing the package never starts an exporter."""

from interview_prep.llm.telemetry.client import ObservedClient
from interview_prep.llm.telemetry.context import record_response_model
from interview_prep.llm.telemetry.exporters import configure_telemetry
from interview_prep.llm.telemetry.log_config import configure_logging
from interview_prep.llm.telemetry.tracing import span

__all__ = ["ObservedClient", "configure_logging", "configure_telemetry", "record_response_model", "span"]
