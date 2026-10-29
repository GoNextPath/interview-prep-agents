# Model configuration and local runs

Use this guide to select models, run the CLI, and diagnose failures. For client ownership,
provider extensions, and UI integration, see [LLM architecture](llm-architecture.md).
[ADR 0001](adr/0001-configurable-llm-clients.md) records the proposed decisions.

## Install and run without credentials

Follow [CONTRIBUTING.md](../CONTRIBUTING.md) to clone and activate a virtual environment:

```sh
pip install -e ".[dev]"
make run-mock
```

The packaged registry and agent assignments select deterministic mocks. No API credentials or
model SDKs are required. Mock questions and keyword scoring are development fixtures, not real
answer-quality evaluations. `make help` lists the available commands.

## Registry and precedence

Configuration is split into two JSON files:

- [`llm/models.json`](../src/interview_prep/llm/models.json): reusable model IDs and a `default` ID.
  Each model has a `provider` and vendor `model`. OpenAI requires `api_key_env`; Ollama requires
  `base_url`. Multiple IDs can use the same provider.
- [`agents/agents.json`](../src/interview_prep/agents/agents.json): assignments for
  `question_generator`, `answer_evaluator`, and `feedback`. Metrics uses deterministic Python.

Model selection happens when clients are constructed, in this order:

1. `LLM_MODE=mock` forces every configured model-backed agent to a mock.
2. `LLM_QUESTION_GENERATOR`, `LLM_ANSWER_EVALUATOR`, or `LLM_FEEDBACK` selects a registry ID.
3. The corresponding agent assignment selects an ID.
4. The registry default supplies an ID when the assignment is absent.

`LLM_MODE` accepts only `mock` or `live`. When unset, registry selections and agent overrides
are permitted; checked-in selections are all mocks. Empty or unknown selectors fail instead of
falling back. Global mock mode ignores agent selectors but still requires structurally valid
configuration. Injected clients bypass selection for their agents.

To add a model, add its ID under `models` using an implemented provider, then select that ID.
Recreate the pipeline after changing files or selectors. Both files are validated together;
unknown providers/agents, duplicate keys, unknown settings, and dangling references are errors.

Store credential environment-variable names in JSON, never actual secrets. Export values in
your shell, or load a trusted local `.env` explicitly with `set -a; . ./.env; set +a`.
The application does not load `.env` automatically. Never commit `.env`.

## Select one hosted model

Install the optional SDK and export your own `OPENAI_API_KEY` securely:

```sh
pip install -e ".[dev,openai]"
export LLM_MODE=live
export LLM_QUESTION_GENERATOR=openai-fast
python -m interview_prep --topic databases --answer "I would add an index."
```

Only the generator uses OpenAI; the remaining assignments still select mocks. Hosted calls may
incur charges. Select registry IDs such as `openai-fast`, not raw vendor model names.
Credentials are checked only when constructing a selected hosted client. Unsupported providers,
including Anthropic, fail validation rather than switching providers.

## Mix local, hosted, and mock clients

With [Ollama](https://docs.ollama.com/) installed:

```sh
ollama serve  # Another terminal; skip if already running.
ollama pull llama3.2
```

Then select models independently:

```sh
export LLM_MODE=live
export LLM_QUESTION_GENERATOR=openai-fast
export LLM_ANSWER_EVALUATOR=mock
export LLM_FEEDBACK=local
python -m interview_prep --topic teamwork --answer "My action led to a result."
```

The `local` entry uses `llama3.2` at `http://localhost:11434`, with no hosted API key.
Authenticated Ollama servers are unsupported. Plain HTTP is restricted to loopback hosts;
remote endpoints require HTTPS. Ollama requests bypass environment proxies and reject redirects.
Custom OpenAI endpoints are unsupported.

## External configuration

Deployments can supply JSON files without editing the installed package:

```sh
LLM_MODE=live python -m interview_prep \
  --models-config /etc/interview-prep/models.json \
  --agents-config /etc/interview-prep/agents.json
```

Without either flag, packaged mock-safe defaults apply. With only `--models-config`, the loader
looks for `agents.json` beside that file. With only `--agents-config`, model definitions remain
packaged. Missing or invalid external files fail without silently switching to packaged files;
errors identify the file and explain sibling lookup when applicable. Environment selectors keep
their precedence. Version configuration with your deployment and supply credentials separately.

Embedding applications can use `load_registry("models.json", agents_path="agents.json")` and
pass the result to `Pipeline`; see [client ownership](llm-architecture.md#client-interface-and-ownership).

## CLI options

Run `python -m interview_prep --help` for all options.

| Option | Purpose/default |
| --- | --- |
| `--topic`, `--difficulty` | Interview topic and easy/medium/hard difficulty. |
| `--answer` | Answer text; otherwise the CLI prompts interactively. |
| `--models-config`, `--agents-config` | External JSON configuration paths. |
| `--log-level` | Override `INTERVIEW_PREP_LOG_LEVEL`; default `WARNING`. |
| `--request-timeout` | Override `LLM_TIMEOUT_SECONDS`; default 30 seconds. |
| `--progress-interval` | Override `LLM_PROGRESS_INTERVAL_SECONDS`; default 10 seconds. |
| `--no-progress` | Hide progress; `--progress` enables it (the default). |
| `--traceback` | Diagnostic traceback instead of a concise error. |

Timeout must be positive and finite; progress interval must be nonnegative and finite. Explicit
CLI values take precedence, including when the overridden environment value is invalid. An
interval of zero keeps start/final events but disables waiting updates. Heartbeats report elapsed
time, not a completion percentage; they do not extend timeouts or retry requests.

Provider transports use network timeouts, not a hard total deadline. Both Ollama Make targets
allow 120 seconds by default to accommodate cold starts, and retain ten-second heartbeats:

```sh
make run-ollama IP_TIMEOUT_SECONDS=180 IP_PROGRESS_INTERVAL=5
make trace-ollama IP_LOG_LEVEL=DEBUG
```

Make uses `IP_LOG_LEVEL`, `IP_TIMEOUT_SECONDS`, and `IP_PROGRESS_INTERVAL`, avoiding collisions
with generic shell variables. These are Make overrides; direct Python runs use the environment
variables in the table above. Adapters cap output at 1,024 tokens and do not retry automatically.

## Logging and an Ollama trace

Ordinary practice uses `make run-mock` or `make run-ollama`: WARNING logs, telemetry off. Mock
runs hide progress; Ollama retains progress for long calls. Diagnostic targets `make trace-mock`
and `make trace-ollama` enable INFO logs and console spans. Trace collection and log thresholds
are independent: ERROR-only logging does not suppress spans.

Console tracing needs no account or collector:

```sh
pip install -e ".[dev,telemetry]"
ollama serve  # Separate terminal; skip if already running.
ollama pull llama3.2
ollama run llama3.2 "Reply with ready."
mkdir -p logs
make trace-ollama 2> logs/ollama.log
```

Warm-up helps avoid cold-start timeouts. To use another installed model, change the `local`
entry's vendor `model` field or provide an external registry. All three model-backed agents use
Ollama in this Make target; it needs neither OpenAI dependencies nor hosted credentials.
Local models may return invalid output, which fails validation rather than triggering a fallback.

Logs, progress, and console spans use stderr. Questions, answer prompts, feedback, and brief
failure notices use stdout, so stderr redirection does not hide a failed round. The log contains
the detailed error. Redirect stdout separately only if you intend to save interview content.

Log levels are `DEBUG`, `INFO`, `WARNING`, `ERROR`, and `CRITICAL`. INFO identifies client
selection, provider/model, call start/completion, response model when reported, duration, and
trace ID. DEBUG adds transport settings. ERROR records failures by type without raw exceptions.
A successful round has a parent span, three selection spans, and three generation spans sharing
a trace ID. Call success means transport/JSON parsing succeeded; agent validation may still fail.

Application diagnostics exclude prompts, answers, generated content, keys, and provider error
bodies. Validation errors identify safe paths such as `answer_evaluator.criteria[0].rationale`.
The OpenAI SDK has separate logging controls: `OPENAI_LOG=debug` can expose request contents.
Avoid it with sensitive data. Pinning the endpoint does not isolate SDK organization/project,
custom-header, or transport environment settings.

`INTERVIEW_PREP_TELEMETRY` accepts `off` (default), `console`, or `otlp`. OTLP/HTTP export is an
explicit network opt-in, configured using settings such as
`OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318`. SDK sampling supports settings such as
`OTEL_TRACES_SAMPLER=always_off`. See [OpenTelemetry exporters](https://opentelemetry.io/docs/languages/python/exporters/).
This integration provides traces and ordinary Python logs, not an evaluation backend or metric exporter.

Local `*.log` files and `logs/` are Git-ignored. `make clean-logs` removes root `.log` files and
`.log` files under `logs/`, preserving other files and directories. `make clean` is an alias;
neither command removes caches or build artifacts. Logs elsewhere are not deleted.

## Tests and troubleshooting

```sh
pip install -e ".[dev,openai,telemetry]"
make check
```

Collection always isolates model settings and blocks DNS/sockets, including local Ollama,
even with `--live-models`. Offline test execution also stays protected. Only authorized live
integration execution (including setup/teardown) restores the original environment and network;
protection is reapplied afterward, including on failure. CI also forces mock mode. Minimal `.[dev]` installs run core tests;
optional SDK tests skip when their dependencies are absent.

Real OpenAI smoke tests live outside default collection and require explicit opt-in:

```sh
pytest integration_tests --live-models
```

They may incur charges, require the SDK and `OPENAI_API_KEY`, and refuse execution in CI.
Without opt-in, root/IDE discovery deselects live tests with a warning. Collection-only makes no
calls. See [integration tests](../integration_tests/README.md).

| Error | Action |
| --- | --- |
| Unknown model ID | Select a registered ID, not a vendor name; remove empty overrides. |
| Missing configuration file | Check the path in the error; pass both file flags if they are not siblings. |
| Missing credential | Export it for the selected provider, or select mock mode. |
| Optional SDK missing | Install the relevant extra, or select mock/local inference. |
| HTTP 401/403 | Check credentials and model/account access. |
| HTTP 404 | Check model/endpoint names; ensure the local model was pulled. |
| HTTP 429 | Check rate limits or quota; no automatic retries occur. |
| Timeout | Warm the local model or increase the network timeout. |
| Invalid model response | Inspect the named field path and model/prompt choice; response values are not logged. |
| Configuration change has no effect | Recreate clients and check global mock mode and selectors. |

The CLI exits with 2 for configuration errors and 1 for model errors. Diagnostic details go to
stderr; a short notice stays on stdout. `--traceback` is an explicit development option.
