# LLM client architecture and extension guide

For installation, model selection, CLI flags, and troubleshooting, see
[model configuration](llm.md). [ADR 0001](adr/0001-configurable-llm-clients.md) explains the decisions.
The client is synchronous because the pipeline is synchronous. Agent teams own prompt quality,
rubric design, and future prompt manifests; the current integrations and mocks are starting points.

## Code organization

Paths are relative to `src/interview_prep/`.

| Location | Responsibility |
| --- | --- |
| `__main__.py` | CLI parsing, configuration resolution, and console round orchestration. |
| `agents/agents.json` | Agent-to-model assignments. |
| `agents/response_validation.py` | Validate generated fields before building domain objects. |
| `llm/contracts.py` | Provider-independent request and generation protocol. |
| `llm/factory.py`, `llm/options.py` | Client construction/cleanup and validated runtime options. |
| `llm/models.json` | Development model definitions and default. |
| `llm/providers/` | OpenAI, Ollama, and mock implementations plus shared response/error helpers. |
| `llm/registry/` | Data types, file loading, model selection, and assignment checks. |
| `llm/registry/validators/` | Common fields and per-provider configuration rules. |
| `llm/telemetry/` | Observed-client wrapper, call context, spans, log configuration, and exporters. |
| `progress/events.py` | Provider-neutral `CallIdentity`, progress events, and callback type. |
| `progress/reporter.py`, `progress/console.py` | Heartbeat lifecycle and console rendering. |

Package initializers expose public names. Validation functions do not need classes. Configuration
validation belongs to the registry; generated-response validation belongs to the agents.
`build_parser()` defines the CLI; `main()` resolves configuration and injects it into `run_round()`.

## Client interface and ownership

Clients implement `generate(Request) -> dict`. Requests carry a task, system instruction, and
JSON-compatible input. Each agent validates its generated fields before constructing existing
shared domain objects. The evaluator computes the mean of criterion scores in Python.

```python
from interview_prep.llm import MockClient, load_registry
from interview_prep.pipeline import Pipeline

registry = load_registry("models.json", agents_path="agents.json")
with Pipeline(registry=registry, clients={"question_generator": MockClient()}) as pipeline:
    question = pipeline.ask("teamwork")
```

The pipeline owns clients it creates; injected clients remain caller-owned. Use its context
manager, or call `pipeline.close()` in `finally`. For an independently created client, call
`close_client(client)` in `finally`. Plain injected clients need only the generation protocol;
cleanup is used when supported. Standalone `QuestionGenerator`, `AnswerEvaluator`, and
`FeedbackAgent` instances also support `close()` and context-manager cleanup. They close only
clients they created; injected clients remain caller-owned. For example:

```python
from interview_prep.agents import QuestionGenerator
from interview_prep.models import Difficulty

with QuestionGenerator() as generator:
    question = generator.generate("teamwork", Difficulty.MEDIUM)
```

Explicit injection takes precedence over model selection for that agent. Remaining clients use
the supplied registry and environment selectors.

The observed wrapper surrounds factory-created calls with safe logs, spans, and progress.
Adapters retain transport responsibilities and optional SDK imports. Provider metadata is recorded
with `record_response_model`; the wrapper never needs the generated content for instrumentation.
A plain `CallIdentity` supplies agent/provider/model identity to logs and progress. The telemetry
layer translates it into OpenTelemetry attribute names, keeping the progress package independent
of those conventions. Absent trace IDs remain `None` in events and display as `-` only in logs.

## Add a provider

1. Add a client module under `llm/providers/` and export it from that package. Keep SDK imports lazy
   and SDK dependencies optional.
2. Add provider settings validation under `llm/registry/validators/` and export the validator.
3. Register the name in `registry/definitions.py` and dispatch validation in `registry/loader.py`.
   A missing validator must fail rather than skip checks.
4. Add explicit construction in `llm/factory.py` without importing provider types into agents.
5. Add recorded transport, malformed-output, credential/configuration, and cleanup tests.

Preserve the shared domain contracts. Exclude content and credentials from diagnostics; retain
safe status/type hints for failures. A common output-token constant in `llm/options.py` keeps
adapters and diagnostics aligned. Registration remains explicit; there is no plugin-discovery
framework or automatic provider fallback.

## Progress and UI integration

The library produces progress only when a callback is attached. Callbacks receive immutable
`ProgressEvent` objects with call ID, agent/provider/model identity, lifecycle phase, elapsed time,
and optional trace ID. Events contain no prompts, answers, output content, or exception messages.
`dataclasses.asdict(event)` provides JSON-serializable fields.

```python
from queue import SimpleQueue

from interview_prep.llm import ClientOptions
from interview_prep.pipeline import Pipeline

# Use a separate queue and pipeline for each request/session.
events = SimpleQueue()
with Pipeline(
    options=ClientOptions(timeout_seconds=120, progress_interval_seconds=5),
    progress=events.put,
) as pipeline:
    question = pipeline.ask("teamwork")
    outcome = pipeline.submit(question, "My action led to a result.")
```

Callbacks must be fast, nonblocking, and thread-safe. Start/final callbacks run on the caller's
thread; waiting callbacks run on a helper thread. The reporter stops and joins the helper before
emitting the terminal event. A blocking callback can delay completion; enqueue events rather than
performing UI or network work directly. Observer exceptions are logged by type and do not replace
model results or errors. No heartbeat thread is needed without a callback or with interval zero.

For a UI, run the synchronous pipeline in a backend worker and forward its request-specific
queue through SSE or WebSockets. Send the validated result or overall failure separately: a model
call completing does not guarantee agent validation succeeded. The web layer owns authentication,
session routing, queue cleanup, and disconnect handling. Pipeline metrics and seed cases are
session state; a pipeline should not be shared concurrently between users. Cancellation and token
streaming are not implemented. Injected clients own their instrumentation and progress.

## Telemetry ownership

Embedding applications configure their OpenTelemetry SDK once at startup. Library imports do not
install providers or start exporters. The CLI owns its provider and shuts it down on exit.
`log_config.py` configures application logging; `exporters.py` configures the optional SDK;
`tracing.py` manages spans; `context.py` holds per-call metadata; `client.py` wraps generation.

Span attributes include identity, requested/actual model, outcome, and timing. Failures record
only type and status, without automatic exception events or descriptions. Interruptions have an
explicit interrupted outcome. Application log levels do not enable SDK request-body logging.
See [diagnostic setup](llm.md#logging-and-an-ollama-trace) for console/OTLP and privacy settings.

## Tests

Offline tests are grouped by behavior: registry, factory, options, provider transports, pipeline,
agent response validation, CLI, Makefile, progress, telemetry, and network safeguards. Provider
and exporter tests use recorded transports or in-memory exporters. Root pytest configuration
blocks network access and removes model selectors/credentials during collection, even with
`--live-models`. Original settings and network access are restored only for authorized tests
under `integration_tests/`, including their fixture setup and teardown. Protection returns after
teardown, including failed tests. Offline tests stay guarded in mixed runs. Collection-only
never lifts protection.
