"""Tests for registry."""

import json
from dataclasses import asdict

import pytest

from interview_prep.llm import (
    ConfigurationError,
    load_registry,
)


@pytest.fixture
def registry_data():
    registry = load_registry()
    return {
        "default": registry.default,
        "models": {
            key: {k: v for k, v in asdict(model).items() if v is not None}
            for key, model in registry.models.items()
        },
        "agents": dict(registry.agents),
    }


def write_registry(tmp_path, data):
    path = tmp_path / "models.json"
    path.write_text(json.dumps({key: value for key, value in data.items() if key != "agents"}))
    (tmp_path / "agents.json").write_text(json.dumps(data["agents"]))
    return path


def test_resolution_precedence(tmp_path, registry_data):
    registry_data["agents"]["question_generator"] = "openai-quality"
    config = load_registry(write_registry(tmp_path, registry_data))
    assert config.resolve("question_generator", {}).model == "gpt-4.1"
    assert config.resolve("question_generator", {"LLM_QUESTION_GENERATOR": "local"}).provider == "ollama"
    assert (
        config.resolve(
            "question_generator",
            {
                "LLM_MODE": "mock",
                "LLM_QUESTION_GENERATOR": "invalid",
            },
        ).provider
        == "mock"
    )
    registry_data["agents"] = {}
    assert load_registry(write_registry(tmp_path, registry_data)).resolve("feedback", {}).provider == "mock"


@pytest.mark.parametrize(
    "env",
    [
        {"LLM_MODE": "typo"},
        {"LLM_FEEDBACK": "missing"},
        {"LLM_FEEDBACK": ""},
    ],
)
def test_invalid_selectors_fail(env):
    with pytest.raises(ConfigurationError):
        load_registry().resolve("feedback", env)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d.update(default="missing"),
        lambda d: d["agents"].update(feedback="missing"),
        lambda d: d["agents"].update(metrics="mock"),
        lambda d: d["models"]["local"].update(provider="unknown"),
        lambda d: d["models"]["local"].update(provider=[]),
        lambda d: d["models"]["local"].update(base_url="file:///etc/passwd"),
        lambda d: d["models"]["local"].update(base_url="http://localhost:wrong"),
        lambda d: d["models"]["local"].update(base_url="http://secret:secret@localhost"),
        lambda d: d["models"]["openai-fast"].pop("api_key_env"),
        lambda d: d["models"]["mock"].update(api_key="secret"),
        lambda d: d["models"]["openai-fast"].update(base_url="https://example.org"),
        lambda d: d["models"]["mock"].update(model=""),
        lambda d: d.update(models=[]),
        lambda d: d["agents"].update(feedback=[]),
    ],
)
def test_registry_rejects_invalid_settings(tmp_path, registry_data, mutate):
    mutate(registry_data)
    with pytest.raises(ConfigurationError):
        load_registry(write_registry(tmp_path, registry_data))


def test_invalid_json_and_duplicate_keys(tmp_path):
    path = tmp_path / "models.json"
    for contents in ("{", '{"default":"mock","default":"paid"}'):
        path.write_text(contents)
        with pytest.raises(ConfigurationError):
            load_registry(path)
    with pytest.raises(ConfigurationError):
        load_registry(tmp_path / "missing.json")


def test_custom_agent_file_and_environment_overrides(tmp_path, registry_data):
    model_path = write_registry(tmp_path, registry_data)
    assignments = tmp_path / "custom-agents.json"
    assignments.write_text(json.dumps({"question_generator": "local", "answer_evaluator": "openai-quality"}))
    config = load_registry(model_path, agents_path=assignments)
    assert config.resolve("question_generator", {}).provider == "ollama"
    assert config.resolve("answer_evaluator", {}).model == "gpt-4.1"
    assert config.resolve("feedback", {}).provider == "mock"
    for agent in ("question_generator", "answer_evaluator", "feedback"):
        assert config.resolve(agent, {f"LLM_{agent.upper()}": "openai-fast"}).model == "gpt-4.1-mini"
        assert (
            config.resolve(agent, {"LLM_MODE": "mock", f"LLM_{agent.upper()}": "missing"}).provider == "mock"
        )


@pytest.mark.parametrize("contents", ["{", "[]", '{"feedback":"mock","feedback":"local"}'])
def test_invalid_agent_json_fails(tmp_path, registry_data, contents):
    model_path = write_registry(tmp_path, registry_data)
    (tmp_path / "agents.json").write_text(contents)
    with pytest.raises(ConfigurationError):
        load_registry(model_path)


def test_custom_registry_requires_its_agent_assignments(tmp_path, registry_data):
    model_path = write_registry(tmp_path, registry_data)
    (tmp_path / "agents.json").unlink()
    with pytest.raises(ConfigurationError, match="agent assignments"):
        load_registry(model_path)


@pytest.mark.parametrize(
    "url,allowed",
    [
        ("http://localhost:11434", True),
        ("http://127.0.0.1:11434", True),
        ("http://[::1]:11434", True),
        ("http://gpu-box.lan:11434", False),
        ("https://gpu-box.lan:11434", True),
    ],
)
def test_ollama_plain_http_is_loopback_only(tmp_path, url, allowed):
    path = tmp_path / "models.json"
    path.write_text(
        json.dumps(
            {
                "default": "local",
                "models": {"local": {"provider": "ollama", "model": "fixture", "base_url": url}},
            }
        )
    )
    (tmp_path / "agents.json").write_text("{}")
    if allowed:
        assert load_registry(path).resolve("feedback", {}).base_url == url
    else:
        with pytest.raises(ConfigurationError, match="require HTTPS"):
            load_registry(path)


def test_missing_assignment_error_names_path_and_sibling_lookup(tmp_path, registry_data):
    model_path = write_registry(tmp_path, registry_data)
    assignments = tmp_path / "agents.json"
    assignments.unlink()
    with pytest.raises(ConfigurationError) as error:
        load_registry(model_path)
    message = str(error.value)
    assert str(assignments) in message
    assert "beside --models-config" in message and "--agents-config" in message


def test_invalid_json_error_names_config_file(tmp_path):
    path = tmp_path / "malformed-models.json"
    path.write_text("{")
    with pytest.raises(ConfigurationError) as error:
        load_registry(path)
    assert str(path) in str(error.value) and "invalid JSON syntax" in str(error.value)


def test_provider_without_validator_is_rejected(monkeypatch):
    from interview_prep.llm.registry import loader
    from interview_prep.llm.registry.validators import common

    monkeypatch.setattr(common, "PROVIDERS", common.PROVIDERS | {"future"})
    with pytest.raises(ConfigurationError, match="No configuration validator"):
        loader._parse_model("future-model", {"provider": "future", "model": "fixture"})
