# Live-provider integration suite

This suite makes real provider calls and may incur charges. It is separate from the default
offline `tests/` suite and is not collected by ordinary `pytest`. Its configuration does not
relax the offline suite's network blocking.

Install the optional provider SDK and export your own `OPENAI_API_KEY` securely:

```sh
pip install -e ".[dev,openai]"
pytest integration_tests --live-models
```

Both the directory and opt-in flag are intentional. Without the flag, live tests are deselected
with a warning, allowing `pytest .` and IDE runs to continue with offline tests. With the flag,
the suite refuses execution in CI or without credentials. Invalid credentials and provider errors fail the test rather
than falling back to mocks. The smoke test explicitly selects the registered OpenAI model,
regardless of shell model selectors.

To inspect the suite without any model calls:

```sh
pytest integration_tests --collect-only
```

Collection remains network-blocked and credential-free even with `--live-models`. Original
credentials/selectors and network access are restored only while an authorized integration test
runs, including setup and teardown, then guarded again. Mixed runs keep offline imports and
tests protected. Collection-only never lifts the guard.

Normal development and CI checks remain offline:

```sh
pytest
```

Local Ollama tracing is a separate manual walkthrough in [model configuration](../docs/llm.md#logging-and-an-ollama-trace).
