"""Tests for factory."""

import pytest

from interview_prep.llm import ConfigurationError, MockClient, Request, close_client, create_client
from interview_prep.llm.providers import OllamaClient
from interview_prep.llm.registry import PROVIDERS, Model, Registry


def test_mocks_do_not_construct_provider_clients(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Mock mode constructed a provider client")

    monkeypatch.setattr("interview_prep.llm.providers.OpenAIClient", forbidden)
    monkeypatch.setattr("interview_prep.llm.providers.OllamaClient", forbidden)
    client = create_client(
        "question_generator", env={"LLM_MODE": "mock", "LLM_QUESTION_GENERATOR": "openai-fast"}
    )
    request = Request("question_generator", "", {"topic": "databases", "difficulty": "hard"})
    assert client.generate(request) == client.generate(request)


def test_credentials_only_required_for_selected_provider():
    with pytest.raises(ConfigurationError, match="OPENAI_API_KEY"):
        create_client("feedback", env={"LLM_FEEDBACK": "openai-fast"})
    assert isinstance(create_client("feedback", env={}).client, MockClient)
    assert isinstance(create_client("feedback", env={"LLM_FEEDBACK": "local"}).client, OllamaClient)


def test_factory_passes_model_and_credentials(monkeypatch):
    seen = []
    monkeypatch.setattr("interview_prep.llm.providers.OpenAIClient", lambda *args: seen.append(args))
    create_client("feedback", env={"LLM_FEEDBACK": "openai-quality", "OPENAI_API_KEY": "test-key"})
    assert seen == [("gpt-4.1", "test-key", 30.0)]


def test_global_mock_mode_overrides_every_agent():
    for agent in ("question_generator", "answer_evaluator", "feedback"):
        client = create_client(agent, env={"LLM_MODE": "mock", f"LLM_{agent.upper()}": "missing"})
        assert isinstance(client.client, MockClient)


def test_dispatch_is_explicit_for_unknown_and_supported_providers():
    for provider in PROVIDERS:
        model = Model(
            provider,
            "fixture",
            "OPENAI_API_KEY" if provider == "openai" else None,
            "http://localhost" if provider == "ollama" else None,
        )
        config = Registry("example", {"example": model}, {})
        # OpenAI intentionally has no credential: dispatch must reach its own configuration error.
        if provider == "openai":
            with pytest.raises(ConfigurationError, match="OPENAI_API_KEY"):
                create_client("feedback", registry=config, env={})
        else:
            close_client(create_client("feedback", registry=config, env={}))
    config = Registry("unknown", {"unknown": Model("unsupported", "fixture")}, {})
    with pytest.raises(ConfigurationError, match="No adapter for provider"):
        create_client("feedback", registry=config, env={})


def test_factory_forwards_timeout_to_both_providers(monkeypatch):
    seen = []
    monkeypatch.setattr("interview_prep.llm.providers.OpenAIClient", lambda *args: seen.append(args))
    monkeypatch.setattr("interview_prep.llm.providers.OllamaClient", lambda *args: seen.append(args))
    create_client(
        "feedback",
        env={"LLM_FEEDBACK": "openai-fast", "OPENAI_API_KEY": "fixture", "LLM_TIMEOUT_SECONDS": "120"},
    )
    create_client("feedback", env={"LLM_FEEDBACK": "local", "LLM_TIMEOUT_SECONDS": "90"})
    assert seen == [("gpt-4.1-mini", "fixture", 120), ("llama3.2", "http://localhost:11434", 90)]
