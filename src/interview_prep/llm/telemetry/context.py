"""Per-call context shared by the observer and provider response metadata hooks."""

from contextvars import ContextVar

from interview_prep.progress.events import CallIdentity

call_span = ContextVar("interview_prep_llm_span", default=None)
call_metadata = ContextVar("interview_prep_llm_metadata", default=None)


def record_response_model(model: object) -> None:
    metadata = call_metadata.get()
    if metadata is not None and isinstance(model, str) and model:
        metadata["response_model"] = model
        current = call_span.get()
        if current is not None:
            current.set_attribute("gen_ai.response.model", model)


def span_attributes(identity: CallIdentity) -> dict:
    """Translate neutral call data into telemetry names at the telemetry boundary."""
    attributes = {
        "gen_ai.agent.name": identity.agent,
        "gen_ai.provider.name": identity.provider,
        "gen_ai.request.model": identity.model,
        "gen_ai.operation.name": "chat",
        "interview_prep.llm.mock": identity.provider == "mock",
    }
    if identity.model_id is not None:
        attributes["interview_prep.llm.model_id"] = identity.model_id
    return attributes
