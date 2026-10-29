"""Validated client runtime options and shared numeric limits."""

import math
from collections.abc import Mapping
from dataclasses import dataclass

from interview_prep.llm.contracts import ConfigurationError

MAX_OUTPUT_TOKENS = 1024


def validate_seconds(value: object, *, name: str, allow_zero: bool = False) -> float:
    """Validate programmatic values without accepting booleans or numeric strings."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ConfigurationError(f"{name} must be a finite number of seconds")
    if value < 0 or (value == 0 and not allow_zero):
        raise ConfigurationError(f"{name} must be {'nonnegative' if allow_zero else 'positive'} and finite")
    return float(value)


def parse_seconds(value: str, *, name: str, allow_zero: bool = False) -> float:
    try:
        number = float(value)
    except ValueError:
        raise ConfigurationError(f"{name} must be a finite number of seconds") from None
    return validate_seconds(number, name=name, allow_zero=allow_zero)


@dataclass(frozen=True)
class ClientOptions:
    timeout_seconds: float = 30.0
    progress_interval_seconds: float = 10.0

    def __post_init__(self) -> None:
        validate_seconds(self.timeout_seconds, name="timeout_seconds")
        validate_seconds(self.progress_interval_seconds, name="progress_interval_seconds", allow_zero=True)

    @classmethod
    def from_env(
        cls,
        env: Mapping[str, str],
        *,
        timeout_seconds: float | None = None,
        progress_interval_seconds: float | None = None,
    ) -> "ClientOptions":
        """Resolve explicit overrides first, so overridden environment values are never parsed."""
        if timeout_seconds is None:
            timeout_seconds = parse_seconds(env.get("LLM_TIMEOUT_SECONDS", "30"), name="LLM_TIMEOUT_SECONDS")
        if progress_interval_seconds is None:
            progress_interval_seconds = parse_seconds(
                env.get("LLM_PROGRESS_INTERVAL_SECONDS", "10"),
                name="LLM_PROGRESS_INTERVAL_SECONDS",
                allow_zero=True,
            )
        return cls(timeout_seconds, progress_interval_seconds)
