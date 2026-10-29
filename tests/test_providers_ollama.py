"""Tests for providers ollama."""

import json
from dataclasses import asdict
from io import BytesIO
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler
from urllib.request import Request as HTTPRequest

import pytest

from interview_prep.llm import (
    ModelError,
    Request,
    create_client,
    providers,
)
from interview_prep.llm.providers import OllamaClient, ollama


def test_ollama_adapter_uses_nonstreaming_json(monkeypatch):
    def respond(request, timeout):
        payload = json.loads(request.data)
        assert request.full_url == "http://localhost:11434/api/chat"
        assert payload["model"] == "llama3.2"
        assert payload["stream"] is False
        assert payload["format"] == "json"
        assert timeout == 30
        return BytesIO(json.dumps({"done": True, "message": {"content": '{"ok": true}'}}).encode())

    monkeypatch.setattr("interview_prep.llm.providers.ollama.urlopen", respond)
    assert OllamaClient("llama3.2", "http://localhost:11434").generate(Request("feedback", "JSON", {})) == {
        "ok": True
    }


def test_provider_failure_does_not_expose_inputs(monkeypatch):
    def fail(*args, **kwargs):
        raise OSError("private answer and credentials")

    monkeypatch.setattr("interview_prep.llm.providers.ollama.urlopen", fail)
    with pytest.raises(ModelError, match="Ollama request failed") as error:
        OllamaClient("local", "http://localhost").generate(Request("feedback", "", {}))
    assert "private" not in str(error.value)


@pytest.mark.parametrize(
    "body",
    [
        [],
        {},
        {"done": False},
        {"done": True, "done_reason": "length"},
        {"done": True, "message": {"content": "not JSON"}},
        {"done": True, "message": {"content": "[]"}},
    ],
)
def test_ollama_rejects_incomplete_or_invalid_responses(monkeypatch, body):
    monkeypatch.setattr(
        "interview_prep.llm.providers.ollama.urlopen",
        lambda *args, **kwargs: BytesIO(json.dumps(body).encode()),
    )
    with pytest.raises(ModelError):
        OllamaClient("llama3.2", "http://localhost:11434").generate(Request("feedback", "JSON", {}))


@pytest.mark.parametrize("status", [400, 401, 404, 429, 500])
def test_ollama_status_diagnostics_exclude_response_bodies(monkeypatch, status):
    def fail(*args, **kwargs):
        raise HTTPError("http://localhost/api/chat", status, "PRIVATE-BODY", {}, BytesIO(b"PRIVATE-BODY"))

    monkeypatch.setattr(ollama, "urlopen", fail)
    with pytest.raises(ModelError) as error:
        providers.OllamaClient("local", "http://localhost").generate(Request("feedback", "PRIVATE", {}))
    assert f"HTTP {status}" in str(error.value)
    assert "HTTPError" in str(error.value) and "PRIVATE" not in str(error.value)


@pytest.mark.parametrize("error", [TimeoutError("PRIVATE"), URLError("PRIVATE")])
def test_ollama_network_error_type_is_visible(monkeypatch, error):
    def fail(*args, **kwargs):
        raise error

    monkeypatch.setattr(ollama, "urlopen", fail)
    with pytest.raises(ModelError) as result:
        providers.OllamaClient("local", "http://localhost").generate(Request("feedback", "", {}))
    assert type(error).__name__ in str(result.value) and "PRIVATE" not in str(result.value)


def test_ollama_bypasses_environment_proxies_and_rejects_redirects(monkeypatch):
    seen = []

    class Opener:
        def open(self, request, timeout):
            return BytesIO(b"{}")

    def build(*handlers):
        seen.extend(handlers)
        return Opener()

    monkeypatch.setenv("HTTP_PROXY", "http://proxy.invalid")
    monkeypatch.setattr(ollama, "build_opener", build)
    ollama.urlopen(HTTPRequest("http://localhost/api/chat"), timeout=30).close()
    proxy = next(handler for handler in seen if isinstance(handler, ProxyHandler))
    assert proxy.proxies == {}
    redirect = next(handler for handler in seen if isinstance(handler, ollama._NoRedirect))
    with pytest.raises(HTTPError):
        redirect.redirect_request(
            HTTPRequest("https://gpu-box/api/chat"), None, 302, "", {}, "http://other/api/chat"
        )


def test_ollama_uses_configured_timeout_and_emits_failure(monkeypatch):
    events = []

    def timeout(request, timeout):
        assert timeout == 120
        raise TimeoutError("PRIVATE-DETAIL")

    monkeypatch.setattr("interview_prep.llm.providers.ollama.urlopen", timeout)
    client = create_client(
        "feedback", env={"LLM_FEEDBACK": "local", "LLM_TIMEOUT_SECONDS": "120"}, progress=events.append
    )
    with pytest.raises(ModelError):
        client.generate(Request("feedback", "", {}))
    assert [e.phase for e in events] == ["started", "failed"]
    assert "PRIVATE" not in str([asdict(e) for e in events])
