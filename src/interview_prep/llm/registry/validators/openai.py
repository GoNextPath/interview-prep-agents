"""Configuration validation for OpenAI models."""

import re

from interview_prep.llm.contracts import ConfigurationError


def validate_openai_settings(model_id: str, spec: dict) -> None:
    key = spec.get("api_key_env")
    if not isinstance(key, str) or not re.fullmatch(r"[A-Z_][A-Z0-9_]*", key):
        raise ConfigurationError(f"Model {model_id}: api_key_env must name an environment variable")
    if spec.get("base_url") is not None:
        raise ConfigurationError(f"Model {model_id}: custom OpenAI endpoints are not supported")
