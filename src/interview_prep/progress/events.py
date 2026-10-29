"""Content-free progress events and their consumer callback type."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class CallIdentity:
    agent: str
    provider: str
    model: str
    model_id: str | None = None


@dataclass(frozen=True)
class ProgressEvent:
    call_id: str
    agent: str
    provider: str
    model: str
    model_id: str | None
    phase: Literal["started", "waiting", "completed", "failed"]
    elapsed_seconds: float
    trace_id: str | None = None


ProgressCallback = Callable[[ProgressEvent], None]
