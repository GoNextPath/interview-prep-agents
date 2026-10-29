"""Create clients at the composition boundary and release their owned resources."""

import logging
import os
from collections.abc import Mapping

from interview_prep.llm.contracts import ConfigurationError, LLMClient
from interview_prep.llm.options import ClientOptions
from interview_prep.llm.providers.mock import MockClient
from interview_prep.llm.registry import Registry, load_registry
from interview_prep.llm.telemetry import ObservedClient, span
from interview_prep.llm.telemetry.context import span_attributes
from interview_prep.progress import CallIdentity, ProgressCallback

logger = logging.getLogger(__name__)


def create_client(
    agent: str,
    *,
    registry: Registry | None = None,
    env: Mapping[str, str] | None = None,
    options: ClientOptions | None = None,
    progress: ProgressCallback | None = None,
) -> LLMClient:
    env = os.environ if env is None else env
    attributes = {"gen_ai.agent.name": agent, "gen_ai.operation.name": "chat"}
    with span("llm.select_client", attributes) as current:
        model_id, selected = (registry or load_registry()).resolve_selection(agent, env)
        identity = CallIdentity(agent, selected.provider, selected.model, model_id)
        attributes.update(span_attributes(identity))
        if current is not None:
            current.set_attributes(attributes)
        options = options if options is not None else ClientOptions.from_env(env)
        client = _build_client(selected, env, options)
        logger.info(
            "LLM client selected agent=%s provider=%s model_id=%s model=%s",
            agent,
            selected.provider,
            model_id or "forced-mock",
            selected.model,
        )
        return ObservedClient(client, identity, options=options, progress=progress)


def _build_client(selected, env: Mapping[str, str], options: ClientOptions) -> LLMClient:
    if selected.provider == "mock":
        return MockClient()
    from interview_prep.llm.providers import OllamaClient, OpenAIClient

    if selected.provider == "ollama":
        return OllamaClient(selected.model, selected.base_url, options.timeout_seconds)
    if selected.provider != "openai":
        raise ConfigurationError(f"No adapter for provider {selected.provider!r}")
    key = env.get(selected.api_key_env, "")
    if not key.strip():
        raise ConfigurationError(f"Selected OpenAI model requires {selected.api_key_env}")
    return OpenAIClient(selected.model, key, options.timeout_seconds)


def close_client(client: LLMClient) -> None:
    """Release resources when supported, without expanding the injection protocol."""
    closer = getattr(client, "close", None)
    if closer is not None:
        closer()
