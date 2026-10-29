"""Configuration validation and endpoint policy for Ollama models."""

from ipaddress import ip_address
from urllib.parse import urlsplit

from interview_prep.llm.contracts import ConfigurationError


def is_loopback_url(url: str) -> bool:
    hostname = urlsplit(url).hostname
    if hostname == "localhost":
        return True
    try:
        return ip_address(hostname).is_loopback
    except ValueError:
        return False


def validate_ollama_settings(model_id: str, spec: dict) -> None:
    if spec.get("api_key_env") is not None:
        raise ConfigurationError(f"Model {model_id}: api_key_env is only supported for OpenAI")
    url = spec.get("base_url")
    message = f"Model {model_id}: base_url must be an HTTP(S) endpoint without credentials"
    if not isinstance(url, str):
        raise ConfigurationError(message)
    try:
        parsed = urlsplit(url)
        hostname = parsed.hostname
        _ = parsed.port  # Reading the port validates its syntax and range.
    except ValueError:
        raise ConfigurationError(message) from None
    if parsed.scheme not in {"http", "https"} or not hostname:
        raise ConfigurationError(message)
    if parsed.username is not None or parsed.password is not None:
        raise ConfigurationError(message)
    if parsed.query or parsed.fragment:
        raise ConfigurationError(message)
    if parsed.scheme == "http" and not is_loopback_url(url):
        raise ConfigurationError(f"Model {model_id}: non-loopback Ollama endpoints require HTTPS")
