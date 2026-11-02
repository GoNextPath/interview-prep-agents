# interview-prep-agents

An open-source **multi-agent pipeline for interview practice**, built by the Leopard Community.

> **A note for visitors:** this is a study-group project rather than an open community one. The repo is public so members can point to their own work, but we aren't taking contributions from outside the group right now. Thanks for understanding, and for the interest.

Four small agents each do one job and pass their results along:

```mermaid
flowchart LR
    QG[Question Generator] -- question --> AE[Answer Evaluator]
    AE -- score --> FA[Feedback Agent]
    FA -- outcome --> MA[Metrics Agent]
    MA -- new test cases --> QG
```

| Agent | Job | Lives in |
| --- | --- | --- |
| Question Generator | Creates interview questions by topic and difficulty | `src/interview_prep/agents/question_generator.py` |
| Answer Evaluator | Scores a practice answer against a rubric | `src/interview_prep/agents/answer_evaluator.py` |
| Feedback Agent | Turns a score into specific, actionable feedback | `src/interview_prep/agents/feedback.py` |
| Metrics Agent | Logs outcomes and feeds new test cases back to the generator | `src/interview_prep/agents/metrics.py` |

The shared data types the agents pass to each other are in `src/interview_prep/models.py`. **Agree on changes there with the other teams first.** It's the contract that holds the pipeline together.

> **Status:** early scaffold. The pipeline defaults to deterministic mock clients and placeholder output.
> Model-backed agents can opt into OpenAI or local Ollama; agent teams own prompt and evaluation quality.

## Prerequisites

- **Git**
- **[uv](https://docs.astral.sh/uv/)**, which manages Python, the virtual environment and dependencies. Install it once:

  | Platform | Command |
  | --- | --- |
  | macOS / Linux | `curl -LsSf https://astral.sh/uv/install.sh \| sh` (or `brew install uv`) |
  | Windows | `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 \| iex"` (or `winget install --id=astral-sh.uv -e`) |
  | Any, with Python already installed | `pipx install uv` |

  Check it worked with `uv --version`. See the [uv installation guide](https://docs.astral.sh/uv/getting-started/installation/) for other options.

You don't need to install Python separately: if `uv sync` can't find Python 3.12 or newer, it downloads one. You only need your own Python 3.12+ if you use the [pip workflow](#pip-workflow) below.

## Quick start

```bash
git clone https://github.com/GoNextPath/interview-prep-agents.git
cd interview-prep-agents
uv sync --locked --extra dev               # create .venv and install from uv.lock

uv run --locked pytest                     # run the tests
uv run --locked python -m interview_prep   # run one question through the whole pipeline
```

### pip workflow

Steps if you prefer to use pip.  Note: pip doesn't read uv.lock, so the versions on your local may be different than what is used in CI.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

Requires Python 3.12+. No API credentials are needed for tests or the default pipeline.

## Development commands

Run `make help` (or just `make`) to discover available commands:

```sh
make check             # Ruff and offline tests
make run-mock          # Quiet interactive mock round
make run-ollama        # Interactive Ollama round; progress on stderr
make trace-mock        # Mock diagnostics and console tracing
make trace-ollama      # Ollama diagnostics and console tracing
make clean-logs        # Remove local .log files (clean is an alias)
make test-live-list    # Inspect live tests without model calls
make test-live         # Real OpenAI calls; may incur charges
```

The Makefile defaults to locked `uv` commands, matching CI. Run `make install` to create
the Python 3.12+ environment. For pip, use `make install TOOL=pip PYTHON=python3.12`;
subsequent commands also need `TOOL=pip` and use `VENV=.venv` without activation.
Set application logging with `make trace-ollama IP_LOG_LEVEL=DEBUG`.
Choose an install target:

| Command | Installs |
| --- | --- |
| `make install` | Development tools for mock/Ollama work |
| `make install-openai` | Development tools and the OpenAI SDK |
| `make install-telemetry` | Development tools and tracing support |
| `make install-all` | All three extras, matching full CI test coverage |

With uv, each install target synchronizes the environment to its selected extras; use
`make install-all` to keep both optional features installed. Pip installs add extras without
removing previously installed ones. For example, run `make install-all`, `make check`,
then `make trace-mock`.

Use `make test TEST_ARGS="tests/test_pipeline.py -q"` for selected tests,
`make format FILES="src/interview_prep"` for formatting, `make run ARGS="--help"`
for CLI options, and `make smoke` for a non-interactive example that forces mock clients
and disables telemetry regardless of shell settings. For full offline verification before
submitting changes, run `make install-all`, `make check`, and `make smoke`.
Installing SDKs does not enable model calls or trace export. OpenAI calls require your
`OPENAI_API_KEY` and live model selection; see [model configuration](docs/llm.md).
Telemetry defaults to `off`; `console` writes traces to stderr without a collector.
Only `otlp` enables HTTP trace export to a local or remote collector. The trace Make targets
select `console`. Tracing stays optional to keep the base dependency set small.

Before using Ollama, start its server and pull/warm the model named in the registry's `local`
entry; see the [Ollama walkthrough](docs/llm.md#logging-and-an-ollama-trace). Both run targets
use `WARNING` logging and disable telemetry. Mock runs hide progress chatter; Ollama runs keep
progress updates visible. Trace targets use `INFO` logging and enable console spans.

Questions, answer prompts, feedback, and brief failure notices go to stdout. Logs, progress updates, and console spans
go to stderr. Capture diagnostics without mixing them into the practice output:

```sh
mkdir -p logs
make trace-mock 2> logs/mock.log
make trace-ollama 2> logs/ollama.log
```

If a round fails, the practice output shows a brief notice even with diagnostics redirected.
Check the log for the detailed error; response validation names the invalid field without
recording its contents.

Both Ollama targets default to a 120-second network timeout and 10-second waiting updates;
override with `make run-ollama IP_TIMEOUT_SECONDS=180 IP_PROGRESS_INTERVAL=5`. See
[progress and UI integration](docs/llm-architecture.md#progress-and-ui-integration) for the callback API.
Local `.log` files and `logs/` are Git-ignored. `make clean` deletes root-level `.log` files and
`.log` files recursively under `logs/`, preserving other files and directories.
Make is optional; the underlying Python commands remain available in the documentation.

## Model configuration

Each model-backed agent accepts an injected client and can independently select a registered
model. `LLM_MODE=mock` forces credential-free mocks; metrics always uses Python logic.
See [model configuration](docs/llm.md) for hosted/local setup, external deployment configuration,
provider extensions, and troubleshooting. The guide includes a
[code organization map](docs/llm-architecture.md#code-organization), [CLI options](docs/llm.md#cli-options),
and an [Ollama trace walkthrough](docs/llm.md#logging-and-an-ollama-trace).
[ADR 0001](docs/adr/0001-configurable-llm-clients.md) records the proposed decisions.

## Repo layout

```bash
src/interview_prep/
  __main__.py        # CLI parsing, configuration, and practice-round entry point
  models.py          # shared data types (the contract between agents)
  pipeline.py        # wires agents together and owns created clients
  agents/            # agents, agents.json assignments, and response validation
  progress/          # events, heartbeat reporting, and console rendering
  llm/
    contracts.py     # provider-independent request and client protocol
    factory.py       # client creation and cleanup
    options.py       # runtime timeout and heartbeat options
    models.json      # development model definitions and default
    providers/       # OpenAI, Ollama, and mock clients
    registry/        # loading, selection, and configuration validators
    telemetry/       # tracing, logging, exporters, and observed-client wrapper
tests/               # default offline tests, including recorded provider transports
integration_tests/   # separately invoked live-provider smoke tests (may incur charges)
evals/               # evaluation harness and datasets
notebooks/           # example notebooks
docs/                # design doc, MVP, milestones, decisions
```

## Teams

Each area has a small sub-team that stays with it for several weeks. See [`docs/teams.md`](docs/teams.md).

## Contributing

Start with [CONTRIBUTING.md](CONTRIBUTING.md). Contributing is optional and self-paced: help as much or as little as you like.

## Security

This project calls LLMs and is public, so prompt injection, untrusted model output, secrets and dependencies all need care. See [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE)
