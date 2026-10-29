"""Read registry configuration and coordinate validation."""

import json
from importlib.resources import files
from pathlib import Path

from interview_prep.llm.contracts import ConfigurationError
from interview_prep.llm.registry.assignments import validate_agent_assignments, validate_default
from interview_prep.llm.registry.definitions import Model, Registry
from interview_prep.llm.registry.validators import (
    validate_mock_settings,
    validate_model_spec,
    validate_ollama_settings,
    validate_openai_settings,
)
from interview_prep.llm.registry.validators.common import validate_object


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ConfigurationError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _read_config(source, label: str, *, hint: str = "") -> dict:
    try:
        return validate_object(
            json.loads(source.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys), label
        )
    except ConfigurationError as exc:
        raise ConfigurationError(f"Invalid {label} at {source}: {exc}") from None
    except OSError:
        raise ConfigurationError(
            f"Cannot read {label} at {source}: check file existence and permissions. {hint}".rstrip()
        ) from None
    except ValueError:
        raise ConfigurationError(
            f"Cannot read {label} at {source}: invalid JSON syntax. {hint}".rstrip()
        ) from None


def _parse_model(model_id: str, value: object) -> Model:
    spec = validate_model_spec(model_id, value)
    provider = spec["provider"]
    if provider == "mock":
        validate_mock_settings(model_id, spec)
    elif provider == "openai":
        validate_openai_settings(model_id, spec)
    elif provider == "ollama":
        validate_ollama_settings(model_id, spec)
    else:
        raise ConfigurationError(f"No configuration validator for provider {provider!r}")
    return Model(provider, spec["model"], spec.get("api_key_env"), spec.get("base_url"))


def load_registry(path: str | Path | None = None, *, agents_path: str | Path | None = None) -> Registry:
    """Read model definitions and agent assignments, then validate them together."""
    if path is None:
        model_source = files("interview_prep.llm").joinpath("models.json")
    else:
        model_source = Path(path).absolute()
    assignment_hint = ""
    if agents_path is not None:
        assignment_source = Path(agents_path).absolute()
    elif path is not None:
        assignment_source = model_source.with_name("agents.json")
        assignment_hint = "Looked beside --models-config; pass --agents-config to choose another file."
    else:
        assignment_source = files("interview_prep.agents").joinpath("agents.json")

    raw = _read_config(model_source, "model registry")
    if set(raw) != {"default", "models"}:
        raise ConfigurationError(
            "Model registry requires exactly default and models; assignments belong in agents.json"
        )
    agents = _read_config(assignment_source, "agent assignments", hint=assignment_hint)

    models = {}
    model_specs = validate_object(raw["models"], "models")
    for model_id, spec in model_specs.items():
        models[model_id] = _parse_model(model_id, spec)
    default = validate_default(raw["default"], models)
    validate_agent_assignments(agents, models)
    return Registry(default, models, agents)
