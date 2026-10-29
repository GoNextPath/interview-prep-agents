"""Registry data types, supported names, and model selection precedence."""

import os
from collections.abc import Mapping
from dataclasses import dataclass

from interview_prep.llm.contracts import ConfigurationError

AGENTS = ("question_generator", "answer_evaluator", "feedback")
PROVIDERS = {"mock", "openai", "ollama"}


@dataclass(frozen=True)
class Model:
    provider: str
    model: str
    api_key_env: str | None = None
    base_url: str | None = None


@dataclass(frozen=True)
class Registry:
    default: str
    models: Mapping[str, Model]
    agents: Mapping[str, str]

    def resolve(self, agent: str, env: Mapping[str, str] | None = None) -> Model:
        return self.resolve_selection(agent, env)[1]

    def resolve_selection(self, agent: str, env: Mapping[str, str] | None = None) -> tuple[str | None, Model]:
        if agent not in AGENTS:
            raise ConfigurationError(f"Unknown model-backed agent: {agent}")
        env = os.environ if env is None else env
        mode = env.get("LLM_MODE", "live")
        if mode not in {"mock", "live"}:
            raise ConfigurationError("LLM_MODE must be mock or live")
        if mode == "mock":
            return None, Model(provider="mock", model="fixture")
        variable = f"LLM_{agent.upper()}"
        model_id = env.get(variable, self.agents.get(agent, self.default))
        if model_id not in self.models:
            raise ConfigurationError(f"{variable}: unknown registry model ID {model_id!r}")
        return model_id, self.models[model_id]
