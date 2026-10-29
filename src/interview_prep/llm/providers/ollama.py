"""Ollama HTTP adapter with direct connections and no redirects."""

import json
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, ProxyHandler, build_opener
from urllib.request import Request as HTTPRequest

from interview_prep.llm.contracts import ModelError, Request
from interview_prep.llm.options import MAX_OUTPUT_TOKENS
from interview_prep.llm.providers._shared import json_object, provider_error
from interview_prep.llm.telemetry import record_response_model


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise HTTPError(req.full_url, code, "Ollama redirects are disabled", headers, fp)


def urlopen(request, *, timeout):
    # Direct connections keep local interview data away from ambient proxy settings.
    return build_opener(ProxyHandler({}), _NoRedirect()).open(request, timeout=timeout)


class OllamaClient:
    def __init__(self, model: str, base_url: str, timeout_seconds: float = 30.0) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def generate(self, request: Request) -> dict:
        payload = {
            "model": self.model,
            "stream": False,
            "format": "json",
            "messages": [
                {"role": "system", "content": request.system},
                {"role": "user", "content": json.dumps(request.data)},
            ],
            "options": {"num_predict": MAX_OUTPUT_TOKENS},
        }
        try:
            message = HTTPRequest(
                self.base_url + "/api/chat",
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(message, timeout=self.timeout_seconds) as response:
                result = json.load(response)
            if not isinstance(result, dict):
                raise ModelError("Ollama response must be a JSON object")
            record_response_model(result.get("model"))
            if result.get("done") is not True or result.get("done_reason") == "length":
                raise ModelError("Ollama did not complete the response")
            text = result["message"]["content"]
        except ModelError:
            raise
        except HTTPError as exc:
            try:
                failure = provider_error("Ollama", exc, exc.code)
            finally:
                exc.close()
            raise failure from None
        except (URLError, OSError) as exc:
            raise provider_error("Ollama", exc) from None
        except (ValueError, KeyError, TypeError):
            raise ModelError("Ollama returned an invalid response structure") from None
        return json_object(text)
