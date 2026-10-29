"""Validate default and agent references against registered models."""

from collections.abc import Mapping

from interview_prep.llm.contracts import ConfigurationError
from interview_prep.llm.registry.definitions import AGENTS, Model
from interview_prep.llm.registry.validators.common import validate_identifier


def validate_default(value: object, models: Mapping[str, Model]) -> str:
    default = validate_identifier(value, "Default model ID")
    if default not in models:
        raise ConfigurationError(f"Default references unknown model ID {default!r}")
    return default


def validate_agent_assignments(agents: dict, models: Mapping[str, Model]) -> None:
    for agent, model_id in agents.items():
        if agent not in AGENTS:
            raise ConfigurationError(f"Unknown model-backed agent {agent!r}; metrics uses Python logic")
        validate_identifier(model_id, f"Agent {agent} model ID")
        if model_id not in models:
            raise ConfigurationError(f"Agent {agent} references unknown model ID {model_id!r}")
