"""Tests for network safety."""

import os
import socket
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest


def test_network_is_blocked_even_for_local_models():
    with pytest.raises(RuntimeError, match="Network access"):
        socket.create_connection(("localhost", 11434))
    with pytest.raises(RuntimeError, match="Network access"):
        socket.getaddrinfo("api.openai.com", 443)


def test_collection_is_credential_free_and_network_blocked():
    # A module-level probe verifies protection before any autouse fixtures can execute.
    with TemporaryDirectory(prefix="collection-probe-", dir=Path(__file__).parent) as directory:
        path = Path(directory) / "test_probe.py"
        path.write_text("""import os, socket, pytest
assert os.environ["LLM_MODE"] == "mock"
assert "OPENAI_API_KEY" not in os.environ
with pytest.raises(RuntimeError, match="Network access"):
    socket.create_connection(("127.0.0.1", 9))
def test_example(): pass
""")
        env = dict(os.environ, LLM_MODE="live", OPENAI_API_KEY="fixture")
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(path), "--collect-only", "-q"],
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "1 test collected" in result.stdout


@pytest.mark.parametrize("fail_live_test", [False, True])
def test_live_opt_in_guards_mixed_collection_and_restores_after_execution(fail_live_test):
    repo = Path(__file__).resolve().parents[1]
    guarded = """import os, socket, pytest

def assert_guarded():
    assert os.environ["LLM_MODE"] == "mock"
    assert "OPENAI_API_KEY" not in os.environ
    assert "LLM_FEEDBACK" not in os.environ
    with pytest.raises(RuntimeError, match="Network access"):
        socket.create_connection(("127.0.0.1", 9))

assert_guarded()
"""
    with (
        TemporaryDirectory(prefix="offline-probe-", dir=repo / "tests") as offline_dir,
        TemporaryDirectory(prefix="live-probe-", dir=repo / "integration_tests") as live_dir,
    ):
        offline = Path(offline_dir) / "test_offline_probe.py"
        live = Path(live_dir) / "test_live_probe.py"
        offline.write_text(
            guarded
            + """
def test_a_offline_before_live():
    assert_guarded()

def test_c_offline_after_live():
    assert_guarded()
"""
        )
        live.write_text(
            guarded
            + """
def test_b_authorized_live_fixture(monkeypatch):
    assert os.environ["LLM_MODE"] == "live"
    assert os.environ["OPENAI_API_KEY"] == "fixture-key"
    assert os.environ["LLM_FEEDBACK"] == "openai-fast"
    assert socket.create_connection.__name__ != "blocked"
    # No connections are opened. Deliberately mutate state to exercise teardown ordering.
    monkeypatch.setattr(socket, "create_connection", lambda *args, **kwargs: None)
    monkeypatch.setenv("OPENAI_API_KEY", "changed-fixture-key")
"""
            + ('    pytest.fail("intentional fixture failure")\n' if fail_live_test else "")
        )
        (Path(offline_dir) / "conftest.py").write_text("""def pytest_collection_modifyitems(items):
    items.sort(key=lambda item: item.name)
""")
        env = dict(os.environ, LLM_MODE="live", LLM_FEEDBACK="openai-fast", OPENAI_API_KEY="fixture-key")
        env.pop("CI", None)
        command = [sys.executable, "-m", "pytest", str(offline), str(live), "--live-models", "-q"]
        collected = subprocess.run(
            command + ["--collect-only"], env=env, check=False, capture_output=True, text=True
        )
        assert collected.returncode == 0, collected.stdout + collected.stderr
        assert "3 tests collected" in collected.stdout
        result = subprocess.run(command, env=env, check=False, capture_output=True, text=True)
    assert result.returncode == (1 if fail_live_test else 0), result.stdout + result.stderr
    if fail_live_test:
        assert "1 failed, 2 passed" in result.stdout
    else:
        assert "3 passed" in result.stdout
