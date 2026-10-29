"""Tests for telemetry."""

import builtins
import json
import logging
from io import BytesIO

import pytest

from interview_prep.llm import (
    ConfigurationError,
    ModelError,
    Request,
    close_client,
    create_client,
)
from interview_prep.llm.telemetry import ObservedClient, configure_logging, configure_telemetry, span
from interview_prep.models import Difficulty
from interview_prep.pipeline import Pipeline
from interview_prep.progress import CallIdentity


@pytest.fixture
def recorded_spans(monkeypatch):
    trace = pytest.importorskip("opentelemetry.trace")
    sdk = pytest.importorskip("opentelemetry.sdk.trace")
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    exporter = InMemorySpanExporter()
    provider = sdk.TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    monkeypatch.setattr(trace, "get_tracer", provider.get_tracer)
    yield exporter
    provider.shutdown()


@pytest.fixture
def application_logger(monkeypatch):
    logger = logging.getLogger("interview_prep")
    monkeypatch.setattr(logger, "handlers", [])
    monkeypatch.setattr(logger, "level", logging.NOTSET)
    monkeypatch.setattr(logger, "propagate", True)
    return logger


def test_round_spans_share_trace_and_identify_mocks(recorded_spans):
    with span("interview_prep.round", {}):
        pipeline = Pipeline()
        question = pipeline.ask("PRIVATE-TOPIC", Difficulty.EASY)
        pipeline.submit(question, "PRIVATE-ANSWER")
    spans = recorded_spans.get_finished_spans()
    assert len(spans) == 7  # Parent, three selections, three model calls.
    assert len({s.context.trace_id for s in spans}) == 1
    parent = next(s for s in spans if s.name == "interview_prep.round")
    calls = [s for s in spans if s.name == "llm.generate"]
    assert len(calls) == 3
    assert {s.attributes["gen_ai.agent.name"] for s in calls} == {
        "question_generator",
        "answer_evaluator",
        "feedback",
    }
    for call in calls:
        assert call.parent.span_id == parent.context.span_id
        assert call.attributes["gen_ai.provider.name"] == "mock"
        assert call.attributes["gen_ai.response.model"] == "fixture"
        assert call.attributes["interview_prep.llm.mock"] is True
        assert call.attributes["interview_prep.outcome"] == "success"
        assert call.end_time >= call.start_time
    serialized = str([(dict(s.attributes), s.events, s.status) for s in spans])
    assert "PRIVATE" not in serialized


def test_ollama_records_actual_model_and_correlated_logs(monkeypatch, recorded_spans, caplog):
    monkeypatch.setattr(
        "interview_prep.llm.providers.ollama.urlopen",
        lambda *args, **kwargs: BytesIO(
            json.dumps(
                {
                    "done": True,
                    "model": "llama3.2:latest",
                    "message": {"content": '{"ok": true}'},
                }
            ).encode()
        ),
    )
    with caplog.at_level(logging.INFO, logger="interview_prep"):
        client = create_client("feedback", env={"LLM_FEEDBACK": "local"})
        assert client.generate(Request("feedback", "PRIVATE-PROMPT", {"answer": "PRIVATE-ANSWER"})) == {
            "ok": True
        }
    call = next(s for s in recorded_spans.get_finished_spans() if s.name == "llm.generate")
    assert call.attributes["gen_ai.request.model"] == "llama3.2"
    assert call.attributes["gen_ai.response.model"] == "llama3.2:latest"
    assert call.attributes["interview_prep.llm.model_id"] == "local"
    assert f"trace_id={call.context.trace_id:032x}" in caplog.text
    assert "response_model=llama3.2:latest" in caplog.text
    assert "PRIVATE" not in caplog.text


def test_failure_spans_and_logs_exclude_exception_contents(recorded_spans, caplog):
    class FailingClient:
        def generate(self, request):
            raise ModelError("PRIVATE-KEY PRIVATE-ANSWER")

    client = ObservedClient(
        FailingClient(),
        CallIdentity("feedback", "mock", "fixture"),
    )
    with pytest.raises(ModelError):
        client.generate(Request("feedback", "PRIVATE-PROMPT", {}))
    (call,) = recorded_spans.get_finished_spans()
    assert call.status.status_code.name == "ERROR"
    assert call.status.description is None
    assert call.attributes["error.type"] == "ModelError"
    assert not call.events  # No automatic exception message or stack trace.
    assert "error_type=ModelError" in caplog.text
    assert "PRIVATE" not in caplog.text
    assert "PRIVATE" not in str(dict(call.attributes))


def test_missing_credentials_record_configuration_failure(recorded_spans):
    with pytest.raises(ConfigurationError):
        create_client("feedback", env={"LLM_FEEDBACK": "openai-fast"})
    (selection,) = recorded_spans.get_finished_spans()
    assert selection.name == "llm.select_client"
    assert selection.status.status_code.name == "ERROR"
    assert selection.attributes["error.type"] == "ConfigurationError"
    assert selection.attributes["gen_ai.provider.name"] == "openai"


@pytest.mark.parametrize(
    "level,info,debug",
    [
        ("DEBUG", True, True),
        ("INFO", True, False),
        ("WARNING", False, False),
        ("ERROR", False, False),
        ("CRITICAL", False, False),
    ],
)
def test_log_levels_and_stderr(level, info, debug, application_logger, capsys):
    configure_logging(level)
    logger = logging.getLogger("interview_prep.llm")
    logger.info("safe-info")
    logger.debug("safe-debug")
    logger.critical("safe-critical")
    out, err = capsys.readouterr()
    assert ("safe-info" in err) is info
    assert ("safe-debug" in err) is debug
    assert "safe-critical" in err
    assert not out


def test_repeated_logging_setup_and_third_party_isolation(application_logger, capsys):
    third_party = logging.getLogger("openai")
    previous_level = third_party.level
    configure_logging("DEBUG")
    configure_logging("DEBUG")
    logging.getLogger("interview_prep.llm").info("once")
    assert capsys.readouterr().err.count("once") == 1
    assert third_party.level == previous_level


def test_no_telemetry_dependency_required(monkeypatch):
    import builtins

    original = builtins.__import__

    def without_telemetry(name, *args, **kwargs):
        if name.startswith("opentelemetry"):
            raise ImportError("not installed")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", without_telemetry)
    assert create_client("question_generator", env={}).generate(
        Request(
            "question_generator",
            "JSON",
            {"topic": "test", "difficulty": "easy"},
        )
    )["prompt"]
    assert configure_telemetry("off") is None
    with pytest.raises(ConfigurationError, match="telemetry"):
        configure_telemetry("console")


def test_console_exporter_without_network(monkeypatch, capsys):
    trace = pytest.importorskip("opentelemetry.trace")
    pytest.importorskip("opentelemetry.sdk")
    monkeypatch.setattr(trace, "get_tracer_provider", lambda: trace.ProxyTracerProvider())
    providers = []
    monkeypatch.setattr(trace, "set_tracer_provider", providers.append)
    provider = configure_telemetry("console")
    try:
        monkeypatch.setattr(trace, "get_tracer", provider.get_tracer)
        with span("console-example", {"gen_ai.provider.name": "ollama"}):
            pass
        captured = capsys.readouterr()
        assert not captured.out
        result = json.loads(captured.err)
        assert result["name"] == "console-example"
        assert result["attributes"]["gen_ai.provider.name"] == "ollama"
    finally:
        provider.shutdown()


def test_existing_application_provider_is_not_replaced(monkeypatch):
    trace = pytest.importorskip("opentelemetry.trace")
    sdk = pytest.importorskip("opentelemetry.sdk.trace")
    existing = sdk.TracerProvider()
    monkeypatch.setattr(trace, "get_tracer_provider", lambda: existing)
    try:
        with pytest.raises(ConfigurationError, match="already configured"):
            configure_telemetry("console")
    finally:
        existing.shutdown()


def test_cli_flag_overrides_environment(monkeypatch, application_logger):
    from interview_prep import __main__

    monkeypatch.setenv("INTERVIEW_PREP_LOG_LEVEL", "ERROR")
    monkeypatch.setenv("INTERVIEW_PREP_TELEMETRY", "off")
    monkeypatch.setattr("sys.argv", ["interview_prep", "--log-level", "DEBUG"])
    levels = []
    monkeypatch.setattr(__main__, "run_round", lambda **kwargs: levels.append(application_logger.level))
    __main__.main()
    assert levels == [logging.DEBUG]
    monkeypatch.setattr("sys.argv", ["interview_prep"])
    __main__.main()
    assert levels == [logging.DEBUG, logging.ERROR]


def test_otlp_setup_is_explicit_and_uses_http_exporter(monkeypatch):
    trace = pytest.importorskip("opentelemetry.trace")
    pytest.importorskip("opentelemetry.sdk")
    http_export = pytest.importorskip("opentelemetry.exporter.otlp.proto.http.trace_exporter")
    from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

    class OfflineExporter(SpanExporter):
        def export(self, spans):
            return SpanExportResult.SUCCESS

    monkeypatch.setattr(http_export, "OTLPSpanExporter", OfflineExporter)
    monkeypatch.setattr(trace, "get_tracer_provider", lambda: trace.ProxyTracerProvider())
    providers = []
    monkeypatch.setattr(trace, "set_tracer_provider", providers.append)
    provider = configure_telemetry("otlp")
    try:
        assert providers == [provider]
        with provider.get_tracer("test").start_as_current_span("offline-export"):
            pass
        assert provider.force_flush()
    finally:
        provider.shutdown()


def test_openai_response_model_is_reported(monkeypatch, recorded_spans, caplog):
    openai = pytest.importorskip("openai")
    httpx = pytest.importorskip("httpx")
    original = openai.OpenAI

    def respond(request):
        return httpx.Response(
            200,
            json={
                "id": "fixture",
                "object": "chat.completion",
                "created": 0,
                "model": "gpt-4.1-mini-snapshot",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": '{"ok": true}'},
                        "finish_reason": "stop",
                    }
                ],
            },
        )

    monkeypatch.setattr(
        openai,
        "OpenAI",
        lambda **kwargs: original(
            **kwargs,
            http_client=httpx.Client(transport=httpx.MockTransport(respond)),
        ),
    )
    with caplog.at_level(logging.INFO, logger="interview_prep"):
        client = create_client(
            "feedback", env={"LLM_FEEDBACK": "openai-fast", "OPENAI_API_KEY": "PRIVATE-KEY"}
        )
        try:
            client.generate(Request("feedback", "PRIVATE-PROMPT", {}))
        finally:
            close_client(client)
    call = next(s for s in recorded_spans.get_finished_spans() if s.name == "llm.generate")
    assert call.attributes["gen_ai.response.model"] == "gpt-4.1-mini-snapshot"
    assert "response_model=gpt-4.1-mini-snapshot" in caplog.text
    assert "PRIVATE" not in caplog.text
    assert "PRIVATE" not in str(dict(call.attributes))


def test_interrupt_marks_span_without_exception_contents(recorded_spans):
    with pytest.raises(KeyboardInterrupt), span("interrupted-call", {}):
        raise KeyboardInterrupt("PRIVATE")
    (interrupted,) = recorded_spans.get_finished_spans()
    assert interrupted.attributes["interview_prep.outcome"] == "interrupted"
    assert interrupted.attributes["error.type"] == "KeyboardInterrupt"
    assert interrupted.status.status_code.name == "ERROR"
    assert interrupted.status.description is None
    assert not interrupted.events


def test_error_context_without_telemetry(monkeypatch):
    original = builtins.__import__

    def missing(name, *args, **kwargs):
        if name.startswith("opentelemetry"):
            raise ImportError("telemetry not installed")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", missing)
    with pytest.raises(ModelError) as error, span("example", {}):
        raise ModelError("model unavailable")
    assert error.value.__context__ is None


def test_wrapper_close_forwards_once():
    from interview_prep.llm.telemetry import ObservedClient

    closed = []

    class Client:
        def close(self):
            closed.append(True)

    client = ObservedClient(Client(), CallIdentity("feedback", "mock", "fixture"))
    close_client(client)
    close_client(client)
    assert closed == [True]
