"""OpenAI SDK adapter; the optional SDK is imported only when creating a client."""

import json

from interview_prep.llm.contracts import ModelError, Request
from interview_prep.llm.options import MAX_OUTPUT_TOKENS
from interview_prep.llm.providers._shared import json_object, provider_error
from interview_prep.llm.telemetry import record_response_model


class OpenAIClient:
    def __init__(self, model: str, api_key: str, timeout_seconds: float = 30.0) -> None:
        try:
            from openai import APIError, OpenAI
        except ImportError:
            raise ModelError('OpenAI requires: pip install -e ".[openai]"') from None
        # Pin the endpoint; other SDK environment options can still apply (see docs/llm.md).
        self.sdk = OpenAI(
            api_key=api_key, base_url="https://api.openai.com/v1", timeout=timeout_seconds, max_retries=0
        )
        self.model = model
        self._api_error = APIError

    def generate(self, request: Request) -> dict:
        try:
            result = self.sdk.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": request.system},
                    {"role": "user", "content": json.dumps(request.data)},
                ],
                response_format={"type": "json_object"},
                max_completion_tokens=MAX_OUTPUT_TOKENS,
                store=False,
            )
            record_response_model(result.model)
            choice = result.choices[0]
            if choice.finish_reason != "stop" or choice.message.refusal:
                raise ModelError("Model refused or did not complete the response")
            text = choice.message.content
        except ModelError:
            raise
        except self._api_error as exc:
            raise provider_error("OpenAI", exc, getattr(exc, "status_code", None)) from None
        except (IndexError, AttributeError):
            raise ModelError("OpenAI returned an invalid response structure") from None
        return json_object(text)

    def close(self) -> None:
        self.sdk.close()
