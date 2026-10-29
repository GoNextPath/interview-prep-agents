"""Public exports for the shared LLM client package."""

from interview_prep.llm.contracts import ConfigurationError, LLMClient, ModelError, Request
from interview_prep.llm.factory import close_client, create_client
from interview_prep.llm.options import ClientOptions
from interview_prep.llm.providers.mock import MockClient
from interview_prep.llm.registry import load_registry
from interview_prep.progress import ProgressCallback, ProgressEvent

__all__ = [
    "ClientOptions",
    "ConfigurationError",
    "LLMClient",
    "MockClient",
    "ModelError",
    "ProgressCallback",
    "ProgressEvent",
    "Request",
    "close_client",
    "create_client",
    "load_registry",
]
