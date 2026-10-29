"""Shared response decoding and content-free provider error diagnostics."""

import json

from interview_prep.llm.contracts import ModelError


def provider_error(provider: str, error: Exception, status: int | None = None) -> ModelError:
    status = status if isinstance(status, int) else None
    detail = type(error).__name__ + (f", HTTP {status}" if status is not None else "")
    hints = {
        400: "invalid request",
        401: "authentication failed",
        403: "access denied",
        404: "model or endpoint not found; check the model name and availability",
        429: "rate limit or quota exceeded",
    }
    hint = hints.get(status, "check provider availability and connectivity")
    if isinstance(error, TimeoutError) or "Timeout" in type(error).__name__:
        hint = "request timed out; increase the configured timeout or warm the local model"
    return ModelError(f"{provider} request failed ({detail}): {hint}")


def json_object(text: str) -> dict:
    try:
        value = json.loads(text)
    except (ValueError, TypeError):
        raise ModelError("Model response must contain a JSON object") from None
    if not isinstance(value, dict):
        raise ModelError("Model response must contain a JSON object")
    return value
