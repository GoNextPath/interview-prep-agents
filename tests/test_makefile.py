"""Tests for makefile."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize("tool", ["uv", "pip"])
@pytest.mark.parametrize(
    "target,mode,telemetry,level",
    [
        ("smoke", "mock", "off", None),
        ("run-mock", "mock", "off", "WARNING"),
        ("run-ollama", "live", "off", "WARNING"),
        ("trace-mock", "mock", "console", "INFO"),
        ("trace-ollama", "live", "console", "INFO"),
    ],
)
def test_make_run_and_trace_modes(tmp_path, target, mode, telemetry, level, tool):
    if not shutil.which("make"):
        pytest.skip("Make is optional")
    fake_python = tmp_path / "bin" / "python"
    fake_python.parent.mkdir()
    fake_python.write_text(
        f"#!{sys.executable}\n"
        + """import json, os, sys
print(json.dumps({"args": sys.argv[1:], "mode": os.environ["LLM_MODE"],
                  "telemetry": os.environ["INTERVIEW_PREP_TELEMETRY"],
                  "generator": os.environ.get("LLM_QUESTION_GENERATOR")}))
"""
    )
    fake_python.chmod(0o700)
    fake_uv = fake_python.with_name("uv")
    fake_uv.write_text(
        f"#!{sys.executable}\n"
        "import os, sys\n"
        "assert sys.argv[1:4] == ['run', '--locked', 'python']\n"
        f"os.execv({str(fake_python)!r}, [{str(fake_python)!r}, *sys.argv[4:]])\n"
    )
    fake_uv.chmod(0o700)
    env = dict(os.environ, LLM_MODE="live", INTERVIEW_PREP_TELEMETRY="otlp")
    # Parent make overrides must not replace the isolated test runner.
    for name in ("MAKEFLAGS", "MFLAGS", "MAKEOVERRIDES", "RUN", "TOOL"):
        env.pop(name, None)
    for name in ("IP_LOG_LEVEL", "IP_TIMEOUT_SECONDS", "IP_PROGRESS_INTERVAL"):
        env.pop(name, None)
    env.update(LOG_LEVEL="info", TIMEOUT_SECONDS="invalid", PROGRESS_INTERVAL="invalid")
    env["PATH"] = str(fake_python.parent) + os.pathsep + env.get("PATH", "")
    command = ["make", "--no-print-directory", target]
    if tool == "pip":
        command.extend(["TOOL=pip", f"VENV={tmp_path}"])
    result = subprocess.run(
        command,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)  # No echoed Make recipe on stdout.
    assert payload["mode"] == mode and payload["telemetry"] == telemetry
    args = payload["args"]
    if level is not None:
        assert args[args.index("--log-level") + 1] == level
    if target == "smoke":
        assert args[args.index("--answer") + 1]
        assert args[args.index("--topic") + 1] == "system design: URL shortener"
    if target == "run-mock":
        assert "--no-progress" in args
    if mode == "live":
        assert payload["generator"] == "local"
        assert args[args.index("--request-timeout") + 1] == "120"


@pytest.mark.parametrize("target", ["clean", "clean-logs"])
def test_clean_removes_only_logs_in_documented_locations(tmp_path, target):

    if not shutil.which("make"):
        pytest.skip("Make is optional")
    makefile = Path(__file__).resolve().parents[1] / "Makefile"
    (tmp_path / "diagnostics.log").write_text("log")
    logs = tmp_path / "logs" / "nested"
    logs.mkdir(parents=True)
    (logs / "trace.log").write_text("log")
    preserved = [tmp_path / "notes.txt", logs / "keep.txt", tmp_path / "elsewhere" / "keep.log"]
    for path in preserved:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("keep")
    result = subprocess.run(
        ["make", "-f", str(makefile), target], cwd=tmp_path, capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
    assert not (tmp_path / "diagnostics.log").exists()
    assert not (logs / "trace.log").exists()
    assert all(path.read_text() == "keep" for path in preserved)
    assert logs.is_dir()
