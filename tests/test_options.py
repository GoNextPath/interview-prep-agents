"""Tests for options."""

import pytest

from interview_prep.llm import ClientOptions, ConfigurationError, create_client


@pytest.mark.parametrize(
    "name,value",
    [
        ("LLM_TIMEOUT_SECONDS", "0"),
        ("LLM_TIMEOUT_SECONDS", "-1"),
        ("LLM_TIMEOUT_SECONDS", "nan"),
        ("LLM_PROGRESS_INTERVAL_SECONDS", "-1"),
        ("LLM_PROGRESS_INTERVAL_SECONDS", "inf"),
        ("LLM_PROGRESS_INTERVAL_SECONDS", ""),
        ("LLM_TIMEOUT_SECONDS", "wrong"),
    ],
)
def test_invalid_runtime_settings_fail_before_client_creation(name, value):
    with pytest.raises(ConfigurationError, match=name):
        create_client("question_generator", env={name: value})


@pytest.mark.parametrize(
    "settings",
    [
        {"timeout_seconds": True},
        {"timeout_seconds": 0},
        {"progress_interval_seconds": float("nan")},
    ],
)
def test_programmatic_options_are_validated(settings):
    with pytest.raises(ConfigurationError):
        ClientOptions(**settings)


def test_explicit_options_override_invalid_environment_values():
    options = ClientOptions.from_env(
        {"LLM_TIMEOUT_SECONDS": "invalid", "LLM_PROGRESS_INTERVAL_SECONDS": "invalid"},
        timeout_seconds=120,
        progress_interval_seconds=0,
    )
    assert options == ClientOptions(timeout_seconds=120, progress_interval_seconds=0)


def test_unoverridden_invalid_environment_value_still_fails():
    with pytest.raises(ConfigurationError, match="LLM_PROGRESS_INTERVAL_SECONDS"):
        ClientOptions.from_env({"LLM_PROGRESS_INTERVAL_SECONDS": "invalid"}, timeout_seconds=120)
