"""Validate untrusted generated fields before constructing shared domain objects."""

import math

from interview_prep.llm.contracts import ModelError


def text(value: object, *, field: str = "response") -> str:
    if not isinstance(value, str) or not value.strip():
        raise ModelError(f"Invalid model response at {field}: expected nonempty text")
    return value


def texts(value: object, *, field: str = "response") -> list[str]:
    if not isinstance(value, list):
        raise ModelError(f"Invalid model response at {field}: expected a list of text")
    return [text(item, field=f"{field}[{index}]") for index, item in enumerate(value)]


def score(value: object, *, field: str = "response") -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ModelError(f"Invalid model response at {field}: expected a finite numeric score")
    if not 0 <= value <= 1:
        raise ModelError(f"Invalid model response at {field}: score must be between 0 and 1")
    return float(value)


def fields(value: object, required: set[str], *, field: str = "response") -> dict:
    if not isinstance(value, dict) or set(value) != required:
        raise ModelError(
            f"Invalid model response at {field}: requires exactly these fields: {', '.join(sorted(required))}"
        )
    return value
