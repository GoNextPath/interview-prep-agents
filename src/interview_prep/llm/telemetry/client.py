"""Client wrapper for safe call logs, tracing, progress, and resource cleanup."""

import logging
from time import perf_counter

from interview_prep.llm.contracts import LLMClient, Request
from interview_prep.llm.options import MAX_OUTPUT_TOKENS, ClientOptions
from interview_prep.llm.telemetry.context import call_metadata, call_span, span_attributes
from interview_prep.llm.telemetry.tracing import span
from interview_prep.progress import CallIdentity, ProgressCallback, ProgressReporter

logger = logging.getLogger(__name__)


class ObservedClient:
    """Wrap only factory-created clients; injected clients keep their own instrumentation."""

    def __init__(
        self,
        client: LLMClient,
        identity: CallIdentity,
        *,
        options: ClientOptions | None = None,
        progress: ProgressCallback | None = None,
    ) -> None:
        self.client = client
        self.identity = identity
        self.options = options or ClientOptions()
        self.progress = progress
        self._closed = False

    def generate(self, request: Request) -> dict:
        with span("llm.generate", span_attributes(self.identity), client=True) as current:
            token = call_span.set(current)
            metadata = {}
            metadata_token = call_metadata.set(metadata)
            context = current.get_span_context() if current is not None else None
            trace_id = f"{context.trace_id:032x}" if context is not None and context.is_valid else None
            started = perf_counter()
            logger.info(
                "LLM call started agent=%s provider=%s model_id=%s model=%s trace_id=%s",
                *self._identity(),
                trace_id or "-",
            )
            if self.identity.provider == "mock":
                logger.debug("LLM deterministic mock selected; no provider transport")
            else:
                logger.debug(
                    "LLM transport configuration timeout_seconds=%s output_token_limit=%s retries=0",
                    self.options.timeout_seconds,
                    MAX_OUTPUT_TOKENS,
                )
            try:
                with ProgressReporter(
                    self.progress, self.identity, self.options.progress_interval_seconds, trace_id
                ):
                    result = self.client.generate(request)
            except Exception as exc:  # Log only the exception type, then preserve behavior.
                logger.error(
                    "LLM call failed agent=%s provider=%s model_id=%s model=%s error_type=%s trace_id=%s duration_ms=%.2f",
                    *self._identity(),
                    type(exc).__name__,
                    trace_id or "-",
                    (perf_counter() - started) * 1000,
                )
                raise
            else:
                logger.info(
                    "LLM call completed agent=%s provider=%s model_id=%s model=%s response_model=%s trace_id=%s duration_ms=%.2f",
                    *self._identity(),
                    metadata.get("response_model", "unreported"),
                    trace_id or "-",
                    (perf_counter() - started) * 1000,
                )
                return result
            finally:
                call_span.reset(token)
                call_metadata.reset(metadata_token)

    def close(self) -> None:
        if not self._closed:
            closer = getattr(self.client, "close", None)
            if closer is not None:
                closer()
            self._closed = True

    def _identity(self) -> tuple:
        return (
            self.identity.agent,
            self.identity.provider,
            self.identity.model_id or "forced-mock",
            self.identity.model,
        )
