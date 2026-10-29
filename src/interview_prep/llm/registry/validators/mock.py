"""Configuration validation for deterministic mock models."""

from interview_prep.llm.contracts import ConfigurationError


def validate_mock_settings(model_id: str, spec: dict) -> None:
    if spec.get("api_key_env") is not None:
        raise ConfigurationError(f"Model {model_id}: api_key_env is only supported for OpenAI")
    if spec.get("base_url") is not None:
        raise ConfigurationError(f"Model {model_id}: base_url is only supported for Ollama")
