"""Tests for progress."""

import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from threading import Event

import pytest

from interview_prep.llm import ClientOptions, ModelError, Request, create_client
from interview_prep.llm.telemetry import ObservedClient
from interview_prep.pipeline import Pipeline
from interview_prep.progress import CallIdentity

IDENTITY = CallIdentity("answer_evaluator", "ollama", "local-test", "local")


@pytest.mark.parametrize("failure", [None, ModelError("PRIVATE-ANSWER"), KeyboardInterrupt()])
def test_heartbeats_stop_before_terminal_event_and_preserve_results(failure):
    release = Event()
    events = []
    workers = []

    def progress(event):
        events.append(event)
        if event.phase == "waiting":
            workers.append(threading.current_thread())
            if len(workers) == 2:
                release.set()

    class SlowClient:
        def generate(self, request):
            assert release.wait(2), "Periodic updates did not arrive while the model was blocked"
            if failure is not None:
                raise failure
            return {"ok": True}

    client = ObservedClient(
        SlowClient(), IDENTITY, options=ClientOptions(progress_interval_seconds=0.01), progress=progress
    )
    if failure is None:
        assert client.generate(Request("answer_evaluator", "PRIVATE-PROMPT", {})) == {"ok": True}
    else:
        with pytest.raises(type(failure)) as error:
            client.generate(Request("answer_evaluator", "PRIVATE-PROMPT", {}))
        assert error.value is failure
    assert events[0].phase == "started"
    assert events[-1].phase == ("completed" if failure is None else "failed")
    assert len([e for e in events if e.phase == "waiting"]) >= 2
    assert len({e.call_id for e in events}) == 1
    assert all(e.agent == "answer_evaluator" and e.provider == "ollama" for e in events)
    assert [e.elapsed_seconds for e in events] == sorted(e.elapsed_seconds for e in events)
    assert all(not worker.is_alive() for worker in workers)
    assert "PRIVATE" not in str([asdict(e) for e in events])


def test_zero_interval_emits_only_started_and_completed():
    events = []
    client = create_client(
        "question_generator", env={"LLM_PROGRESS_INTERVAL_SECONDS": "0"}, progress=events.append
    )
    client.generate(Request("question_generator", "", {"topic": "databases", "difficulty": "easy"}))
    assert [e.phase for e in events] == ["started", "completed"]


def test_observer_failure_is_sanitized_and_does_not_fail_model(caplog):
    def broken(event):
        raise ValueError("PRIVATE-KEY PRIVATE-ANSWER")

    client = create_client("question_generator", env={}, progress=broken)
    assert client.generate(Request("question_generator", "", {"topic": "test", "difficulty": "easy"}))
    assert "Progress callback failed error_type=ValueError" in caplog.text
    assert "PRIVATE" not in caplog.text


def test_callbacks_can_distinguish_concurrent_calls():
    events = []
    both_running = threading.Barrier(2)

    class ConcurrentClient:
        def generate(self, request):
            both_running.wait(timeout=2)
            return {"ok": True}

    client = ObservedClient(
        ConcurrentClient(),
        IDENTITY,
        options=ClientOptions(progress_interval_seconds=0),
        progress=events.append,
    )
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(client.generate, Request("answer_evaluator", "", {})) for _ in range(2)]
        assert [f.result() for f in futures] == [{"ok": True}, {"ok": True}]
    call_ids = {e.call_id for e in events}
    assert len(call_ids) == 2
    for call_id in call_ids:
        assert [e.phase for e in events if e.call_id == call_id] == ["started", "completed"]


def test_pipeline_progress_is_per_call_without_shared_contract_changes():
    events = []
    pipeline = Pipeline(progress=events.append, options=ClientOptions(progress_interval_seconds=0))
    question = pipeline.ask("teamwork")
    outcome = pipeline.submit(question, "situation action result")
    assert outcome.feedback.summary
    assert [e.agent for e in events if e.phase == "started"] == [
        "question_generator",
        "answer_evaluator",
        "feedback",
    ]
    assert len({e.call_id for e in events}) == 3


def test_progress_uses_plain_call_identity_and_optional_trace_id(caplog):
    import logging

    events = []
    client = create_client(
        "question_generator",
        env={"LLM_MODE": "mock"},
        options=ClientOptions(progress_interval_seconds=0),
        progress=events.append,
    )
    with caplog.at_level(logging.INFO, logger="interview_prep"):
        client.generate(Request("question_generator", "JSON", {"topic": "databases", "difficulty": "easy"}))
    assert all(event.trace_id is None for event in events)
    assert all(event.provider == "mock" and event.agent == "question_generator" for event in events)
    assert client.identity == CallIdentity("question_generator", "mock", "fixture")
    assert "trace_id=-" in caplog.text
