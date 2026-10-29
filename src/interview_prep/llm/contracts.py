"""Small synchronous JSON interface shared by model-backed agents."""

from dataclasses import dataclass
from typing import Any, Protocol


class ConfigurationError(ValueError):
    """Invalid registry, selector, or missing provider configuration."""


class ModelError(RuntimeError):
    """Provider failure or invalid model output; messages exclude request contents."""


@dataclass(frozen=True)
class Request:
    task: str
    system: str
    data: dict[str, Any]


class LLMClient(Protocol):
    def generate(self, request: Request) -> dict[str, Any]: ...
