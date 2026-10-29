"""Common JSON shapes and model metadata validation."""

import re

from interview_prep.llm.contracts import ConfigurationError
from interview_prep.llm.registry.definitions import PROVIDERS


def validate_identifier(value: object, label: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*", value):
        raise ConfigurationError(f"{label} must be a nonempty identifier")
    return value


def validate_object(value: object, label: str) -> dict:
    if not isinstance(value, dict):
        raise ConfigurationError(f"{label} must be a JSON object")
    return value


def validate_model_spec(model_id: str, value: object) -> dict:
    """Validate fields every provider shares before checking provider-specific settings."""
    validate_identifier(model_id, "Model ID")
    spec = validate_object(value, f"Model {model_id}")
    allowed_fields = {"provider", "model", "api_key_env", "base_url"}
    if set(spec) - allowed_fields:
        raise ConfigurationError(f"Model {model_id}: unknown settings (secrets do not belong in JSON)")
    provider = spec.get("provider")
    if not isinstance(provider, str) or provider not in PROVIDERS:
        raise ConfigurationError(f"Model {model_id}: supported providers are {sorted(PROVIDERS)}")
    name = spec.get("model")
    if not isinstance(name, str) or not name.strip():
        raise ConfigurationError(f"Model {model_id}: model must be a nonempty string")
    return spec
