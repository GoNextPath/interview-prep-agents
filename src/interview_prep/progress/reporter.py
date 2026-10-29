"""Periodic progress reporting and heartbeat thread lifecycle."""

import logging
from threading import Event, Thread
from time import monotonic
from typing import Literal
from uuid import uuid4

from interview_prep.progress.events import CallIdentity, ProgressCallback, ProgressEvent

logger = logging.getLogger(__name__)


class ProgressReporter:
    """Callbacks must be fast and thread-safe; waiting events run on a helper thread."""

    def __init__(
        self, callback: ProgressCallback | None, identity: CallIdentity, interval: float, trace_id: str | None
    ) -> None:
        self.callback = callback
        self.identity = identity
        self.interval = interval
        self.trace_id = trace_id
        self.call_id = str(uuid4())
        self.stopped = Event()
        self.thread: Thread | None = None

    def __enter__(self):
        self.started = monotonic()
        self._emit("started")
        if self.callback is not None and self.interval > 0:
            self.thread = Thread(target=self._wait, name=f"llm-progress-{self.call_id}", daemon=True)
            self.thread.start()
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.stopped.set()
        if self.thread is not None:
            self.thread.join()
        self._emit("failed" if exc_type is not None else "completed")

    def _wait(self) -> None:
        while not self.stopped.wait(self.interval):
            self._emit("waiting")

    def _emit(self, phase: Literal["started", "waiting", "completed", "failed"]) -> None:
        if self.callback is None:
            return
        event = ProgressEvent(
            call_id=self.call_id,
            agent=self.identity.agent,
            provider=self.identity.provider,
            model=self.identity.model,
            model_id=self.identity.model_id,
            phase=phase,
            elapsed_seconds=monotonic() - self.started,
            trace_id=self.trace_id,
        )
        try:
            self.callback(event)
        except Exception as exc:  # noqa: BLE001 - observers must not change model results or leak exception contents.
            logger.warning("Progress callback failed error_type=%s", type(exc).__name__)
