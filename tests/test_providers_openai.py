"""Tests for providers openai."""

import json

import pytest

from interview_prep.llm import ModelError, Request, close_client, create_client
from interview_prep.llm.providers import OpenAIClient


@pytest.mark.parametrize(
    "content,finish_reason,refusal,status",
    [
        ('{"ok": true}', "stop", None, 200),
        ('{"ok": true}', "length", None, 200),
        (None, "stop", "Refused", 200),
        ("not JSON", "stop", None, 200),
        ("[]", "stop", None, 200),
        ('{"ok": true}', "stop", None, 429),
    ],
)
def test_openai_adapter_with_recorded_transport(monkeypatch, content, finish_reason, refusal, status):
    openai = pytest.importorskip("openai")
    httpx = pytest.importorskip("httpx")
    original = openai.OpenAI

    calls = []

    def respond(request):
        calls.append(request)
        payload = json.loads(request.content)
        assert payload["model"] == "gpt-4.1-mini"
        assert payload["response_format"] == {"type": "json_object"}
        assert payload["store"] is False
        if status != 200:
            return httpx.Response(
                status, json={"error": {"message": "private provider detail", "type": "rate_limit"}}
            )
        return httpx.Response(
            200,
            json={
                "id": "fixture",
                "object": "chat.completion",
                "created": 0,
                "model": "gpt-4.1-mini",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": content, "refusal": refusal},
                        "finish_reason": finish_reason,
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
    client = OpenAIClient("gpt-4.1-mini", "fixture-key")
    try:
        if content == '{"ok": true}' and finish_reason == "stop" and not refusal and status == 200:
            assert client.generate(Request("feedback", "Return JSON", {})) == {"ok": True}
        else:
            with pytest.raises(ModelError) as error:
                client.generate(Request("feedback", "Return JSON", {}))
            assert "private provider detail" not in str(error.value)
        assert len(calls) == 1
    finally:
        close_client(client)


@pytest.mark.parametrize("status", [401, 404, 429, 500])
def test_openai_status_diagnostics_exclude_response_bodies(monkeypatch, status):
    openai = pytest.importorskip("openai")
    httpx = pytest.importorskip("httpx")
    original = openai.OpenAI

    def respond(request):
        return httpx.Response(status, json={"error": {"message": "PRIVATE-BODY"}})

    monkeypatch.setattr(
        openai,
        "OpenAI",
        lambda **kwargs: original(**kwargs, http_client=httpx.Client(transport=httpx.MockTransport(respond))),
    )
    client = create_client("feedback", env={"LLM_FEEDBACK": "openai-fast", "OPENAI_API_KEY": "fixture"})
    try:
        with pytest.raises(ModelError) as error:
            client.generate(Request("feedback", "PRIVATE", {}))
        assert f"HTTP {status}" in str(error.value) and "PRIVATE" not in str(error.value)
    finally:
        close_client(client)


def test_openai_sdk_receives_configured_timeout():
    pytest.importorskip("openai")
    client = create_client(
        "feedback",
        env={"LLM_FEEDBACK": "openai-fast", "OPENAI_API_KEY": "fixture", "LLM_TIMEOUT_SECONDS": "120"},
    )
    try:
        assert client.client.sdk.timeout == 120
    finally:
        close_client(client)
