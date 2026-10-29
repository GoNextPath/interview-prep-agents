"""Protect offline tests during collection as well as test execution."""

import os
import socket
import warnings
from pathlib import Path

import pytest

LIVE_TESTS = Path(__file__).parent / "integration_tests"


def pytest_addoption(parser):
    parser.addoption(
        "--live-models", action="store_true", help="Allow live-provider integration tests (may cost money)"
    )


def _offline_guard(patch):
    patch.setenv("LLM_MODE", "mock")
    for name in tuple(os.environ):
        if (name.startswith("LLM_") and name != "LLM_MODE") or name in {
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
        }:
            patch.delenv(name)

    def blocked(*args, **kwargs):
        raise RuntimeError("Network access is disabled in unit tests")

    for method in ("connect", "connect_ex", "sendto"):
        patch.setattr(socket.socket, method, blocked)
    patch.setattr(socket, "create_connection", blocked)
    patch.setattr(socket, "getaddrinfo", blocked)


def pytest_configure(config):
    # Snapshot authorization before scrubbing. The MonkeyPatch retains the original environment
    # privately so it can be restored during an authorized live test, never during collection.
    config._live_key_available = bool(os.environ.get("OPENAI_API_KEY", "").strip())
    config._running_in_ci = bool(os.environ.get("CI"))
    config._offline_patch = pytest.MonkeyPatch()
    _offline_guard(config._offline_patch)


def pytest_unconfigure(config):
    patch = getattr(config, "_offline_patch", None)
    if patch is not None:
        patch.undo()


def pytest_collection_modifyitems(config, items):
    live_items = [item for item in items if LIVE_TESTS in item.path.parents]
    if not live_items or config.option.collectonly:
        return
    if not config.getoption("--live-models"):
        config.hook.pytest_deselected(items=live_items)
        items[:] = [item for item in items if item not in live_items]
        warnings.warn(
            pytest.PytestWarning(
                "Live-provider suite deselected; use integration_tests --live-models to opt in"
            ),
            stacklevel=1,
        )
        return
    _require_live_authorization(config)


def _require_live_authorization(config):
    if not config.getoption("--live-models"):
        raise pytest.UsageError("Live-provider tests require --live-models")
    if config._running_in_ci:
        raise pytest.UsageError("Live-provider integration tests are disabled in CI")
    if not config._live_key_available:
        raise pytest.UsageError("Live OpenAI integration tests require OPENAI_API_KEY")


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_protocol(item, nextitem):
    if LIVE_TESTS not in item.path.parents:
        yield
        return
    _require_live_authorization(item.config)
    guard = item.config._offline_patch
    guard.undo()
    try:
        # Include fixture setup and teardown. Reapply after all test monkeypatches are undone,
        # otherwise their teardown could accidentally restore unguarded socket functions.
        yield
    finally:
        _offline_guard(guard)


@pytest.fixture(autouse=True)
def isolate_models_and_block_network(monkeypatch, request):
    if LIVE_TESTS in request.node.path.parents:
        _require_live_authorization(request.config)
        return
    _offline_guard(monkeypatch)
