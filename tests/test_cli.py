"""Tests for cli."""

import json
import logging
import os
import subprocess
import sys

import pytest

from interview_prep.llm import ClientOptions, ConfigurationError, ModelError, ProgressEvent, load_registry
from interview_prep.models import Difficulty


@pytest.mark.parametrize(
    "exception,message,code",
    [
        (ConfigurationError("invalid model selection"), "invalid model selection", 2),
        (ModelError("Ollama request failed (HTTP 404)"), "HTTP 404", 1),
    ],
)
def test_cli_client_errors_are_concise(monkeypatch, capsys, exception, message, code):
    from interview_prep import __main__

    monkeypatch.setattr(sys, "argv", ["interview_prep"])
    monkeypatch.setattr(__main__, "configure_logging", lambda level: None)
    monkeypatch.setattr(__main__, "configure_telemetry", lambda exporter: None)

    def fail(**kwargs):
        raise exception

    monkeypatch.setattr(__main__, "run_round", fail)
    with pytest.raises(SystemExit) as result:
        __main__.main()
    assert result.value.code == code
    stderr = capsys.readouterr().err
    assert stderr.startswith("error: ") and message in stderr
    assert "Traceback" not in stderr


@pytest.mark.parametrize(
    "flag,value", [("--request-timeout", "-1"), ("--request-timeout", "nan"), ("--progress-interval", "-1")]
)
def test_cli_option_errors_name_the_flag(monkeypatch, capsys, flag, value):
    from interview_prep import __main__

    monkeypatch.setattr(sys, "argv", ["interview_prep", flag, value])
    with pytest.raises(SystemExit) as result:
        __main__.main()
    assert result.value.code == 2
    stderr = capsys.readouterr().err
    assert flag in stderr and "LLM_" not in stderr and "Traceback" not in stderr


def test_cli_progress_format_has_no_request_content(capsys):
    from interview_prep.progress.console import print_progress

    print_progress(ProgressEvent("call-id", "answer_evaluator", "ollama", "llama3.2", "local", "waiting", 20))
    captured = capsys.readouterr()
    assert not captured.out
    output = captured.err
    assert "Evaluating answer: still waiting (20s elapsed)" in output


def test_cli_runtime_flags_override_environment(monkeypatch):
    from interview_prep import __main__

    selected = []
    monkeypatch.setattr(__main__, "run_round", lambda **kwargs: selected.append(kwargs))
    monkeypatch.setattr(__main__, "configure_logging", lambda level: None)
    monkeypatch.setattr(__main__, "configure_telemetry", lambda exporter: None)
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "60")
    monkeypatch.setenv("LLM_PROGRESS_INTERVAL_SECONDS", "20")
    monkeypatch.setattr(
        "sys.argv",
        [
            "interview_prep",
            "--topic",
            "test",
            "--difficulty",
            "easy",
            "--answer",
            "action",
            "--request-timeout",
            "120",
            "--progress-interval",
            "0",
            "--no-progress",
        ],
    )
    __main__.main()
    assert selected == [
        {
            "topic": "test",
            "difficulty": Difficulty.EASY,
            "answer": "action",
            "options": ClientOptions(timeout_seconds=120, progress_interval_seconds=0),
            "registry": load_registry(),
            "progress": None,
        }
    ]


def test_round_uses_explicit_options_without_reading_cli_environment(monkeypatch, capsys):
    from interview_prep import __main__

    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "invalid")
    monkeypatch.setenv("LLM_PROGRESS_INTERVAL_SECONDS", "invalid")
    monkeypatch.setattr("sys.argv", ["interview_prep", "--not-a-real-flag"])
    __main__.run_round(
        topic="teamwork",
        difficulty=Difficulty.EASY,
        answer="situation action result",
        options=ClientOptions(progress_interval_seconds=0),
        registry=load_registry(),
    )
    assert "[stub] Overall score: 100%" in capsys.readouterr().out


def test_parser_can_be_used_independently():
    from interview_prep.__main__ import build_parser

    args = build_parser().parse_args(["--topic", "React", "--difficulty", "hard"])
    assert args.topic == "React" and args.difficulty == "hard"


@pytest.mark.parametrize("explicit_agents_path", [True, False])
def test_cli_uses_external_config_files(monkeypatch, tmp_path, capsys, caplog, explicit_agents_path):

    from interview_prep import __main__

    models_path = tmp_path / "deployment-models.json"
    agents_path = tmp_path / ("deployment-agents.json" if explicit_agents_path else "agents.json")
    models_path.write_text(
        json.dumps(
            {
                "default": "deployment-mock",
                "models": {"deployment-mock": {"provider": "mock", "model": "fixture"}},
            }
        )
    )
    agents_path.write_text(json.dumps({"question_generator": "deployment-mock"}))
    arguments = [
        "interview_prep",
        "--models-config",
        str(models_path),
        "--answer",
        "situation action result",
        "--no-progress",
    ]
    if explicit_agents_path:
        arguments.extend(["--agents-config", str(agents_path)])
    monkeypatch.setattr("sys.argv", arguments)
    monkeypatch.setenv("LLM_MODE", "live")
    monkeypatch.setattr(__main__, "configure_logging", lambda level: None)
    monkeypatch.setattr(__main__, "configure_telemetry", lambda exporter: None)
    with caplog.at_level(logging.INFO, logger="interview_prep"):
        __main__.main()
    assert "[stub] Overall score: 100%" in capsys.readouterr().out
    assert "model_id=deployment-mock" in caplog.text


def test_cli_missing_external_config_reports_configuration_error(monkeypatch, tmp_path, capsys):
    from interview_prep import __main__

    monkeypatch.setattr("sys.argv", ["interview_prep", "--models-config", str(tmp_path / "missing.json")])
    monkeypatch.setattr(__main__, "configure_logging", lambda level: None)
    monkeypatch.setattr(__main__, "configure_telemetry", lambda exporter: None)
    with pytest.raises(SystemExit) as result:
        __main__.main()
    assert result.value.code == 2
    stderr = capsys.readouterr().err
    assert "Cannot read model registry" in stderr
    assert "Traceback" not in stderr


def test_mock_trace_separates_results_and_diagnostics():
    pytest.importorskip("opentelemetry.sdk")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "interview_prep",
            "--topic",
            "PRIVATE-TOPIC",
            "--answer",
            "PRIVATE-ANSWER",
            "--log-level",
            "INFO",
        ],
        env=dict(os.environ, LLM_MODE="mock", INTERVIEW_PREP_TELEMETRY="console"),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "Q:" in result.stdout and "[stub] Overall score:" in result.stdout
    assert "PRIVATE-TOPIC" in result.stdout
    assert "LLM call started" not in result.stdout and '"trace_id"' not in result.stdout
    assert "LLM call started" in result.stderr and '"trace_id"' in result.stderr
    assert "model response received" in result.stderr
    assert "PRIVATE" not in result.stderr


def test_invalid_evaluator_response_is_visible_with_stderr_redirected(tmp_path):
    script = """from interview_prep import __main__
original = __main__.Pipeline
class InvalidEvaluatorClient:
    def generate(self, request):
        return {"criteria": [{"criterion": "situation", "score": 1.0, "rationale": {"PRIVATE": "PRIVATE"}}]}
def pipeline(**kwargs):
    return original(clients={"answer_evaluator": InvalidEvaluatorClient()}, **kwargs)
__main__.Pipeline = pipeline
__main__.main()
"""
    log_path = tmp_path / "diagnostics.log"
    with log_path.open("w") as log:
        result = subprocess.run(
            [sys.executable, "-c", script, "--answer", "PRIVATE-ANSWER", "--no-progress"],
            env=dict(os.environ, LLM_MODE="mock", INTERVIEW_PREP_TELEMETRY="off"),
            stdout=subprocess.PIPE,
            stderr=log,
            text=True,
            check=False,
        )
    assert result.returncode == 1
    assert "Q:" in result.stdout
    assert "The practice round couldn't be completed" in result.stdout
    assert "answer_evaluator.criteria" not in result.stdout
    diagnostics = log_path.read_text()
    assert "answer_evaluator.criteria[0].rationale: expected nonempty text" in diagnostics
    assert "PRIVATE" not in diagnostics and "Traceback" not in diagnostics


def test_interactive_answer_prompt_stays_on_stdout_when_stderr_is_redirected(tmp_path):
    log_path = tmp_path / "diagnostics.log"
    with log_path.open("w") as log:
        result = subprocess.run(
            [sys.executable, "-m", "interview_prep", "--no-progress"],
            input="situation action result\n",
            stdout=subprocess.PIPE,
            stderr=log,
            env=dict(os.environ, LLM_MODE="mock", INTERVIEW_PREP_TELEMETRY="off"),
            text=True,
            check=False,
        )
    assert result.returncode == 0
    assert "Your answer: " in result.stdout and "[stub] Overall score: 100%" in result.stdout
    assert "Your answer:" not in log_path.read_text()
