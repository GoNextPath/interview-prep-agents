.DEFAULT_GOAL := help

TOOL ?= uv
PYTHON ?= python3
VENV ?= .venv
FILES ?= src tests
IP_LOG_LEVEL ?= WARNING
IP_TIMEOUT_SECONDS ?= 120
IP_PROGRESS_INTERVAL ?= 10
export IP_LOG_LEVEL IP_TIMEOUT_SECONDS IP_PROGRESS_INTERVAL

ifeq ($(TOOL),uv)
RUN = uv run --locked python -m
else ifeq ($(TOOL),pip)
RUN = "$(VENV)/bin/python" -m
else
$(error TOOL must be uv or pip)
endif

.PHONY: help install lint test check format run smoke
.PHONY: install-openai install-telemetry install-all clean clean-logs
.PHONY: run-mock run-ollama trace-mock trace-ollama test-live-list test-live

help:
	@echo 'Commands (default: TOOL=uv; use TOOL=pip for pip):'
	@echo '  make install              Install project and development tools'
	@echo '  make lint                 Run Ruff checks'
	@echo '  make test                 Run pytest (TEST_ARGS="..." for selection)'
	@echo '  make check                Run lint and tests'
	@echo '  make format               Format src and tests (FILES="..." to override)'
	@echo '  make run                  Run the CLI (ARGS="..." for CLI options)'
	@echo '  make smoke                Run a non-interactive CLI example'
	@echo '  make install-openai       Install development tools and the OpenAI SDK'
	@echo '  make install-telemetry    Install development tools and tracing support'
	@echo '  make install-all          Install all optional SDKs for full test coverage'
	@echo '  make run-mock/run-ollama  Run a mock or local model practice round'
	@echo '  make trace-mock/trace-ollama  Run with console tracing'
	@echo '  make clean-logs           Remove local log files (clean is an alias)'
	@echo '  make test-live-list       Collect live-provider tests without model calls'
	@echo '  make test-live            Run paid live-provider tests explicitly'
	@echo 'Pip setup: make install TOOL=pip PYTHON=python3.12'
	@echo 'Pip commands use VENV=.venv; no environment activation is needed.'

install:
ifeq ($(TOOL),uv)
	uv sync --locked --extra dev
else
	@test -d "$(VENV)" || $(PYTHON) -m venv "$(VENV)"
	"$(VENV)/bin/python" -m pip install -e ".[dev]"
endif

install-openai:
ifeq ($(TOOL),uv)
	uv sync --locked --extra dev --extra openai
else
	@test -d "$(VENV)" || $(PYTHON) -m venv "$(VENV)"
	"$(VENV)/bin/python" -m pip install -e ".[dev,openai]"
endif

install-telemetry:
ifeq ($(TOOL),uv)
	uv sync --locked --extra dev --extra telemetry
else
	@test -d "$(VENV)" || $(PYTHON) -m venv "$(VENV)"
	"$(VENV)/bin/python" -m pip install -e ".[dev,telemetry]"
endif

install-all:
ifeq ($(TOOL),uv)
	uv sync --locked --extra dev --extra openai --extra telemetry
else
	@test -d "$(VENV)" || $(PYTHON) -m venv "$(VENV)"
	"$(VENV)/bin/python" -m pip install -e ".[dev,openai,telemetry]"
endif

lint:
	$(RUN) ruff check .

test:
	$(RUN) pytest $(TEST_ARGS)

check: lint test

format:
	@test -n "$(strip $(FILES))" || (echo 'Specify files: make format FILES="path/to/file.py"'; exit 1)
	$(RUN) ruff format $(FILES)

run:
	$(RUN) interview_prep $(ARGS)

smoke:
	$(RUN) interview_prep --topic "system design: URL shortener" --difficulty medium \
		--answer "The situation is a URL shortener with read-heavy traffic and occasional spikes from popular links. My proposed action is to use a stateless API, random short IDs, and a database with a unique constraint to detect collisions and retry. Redirects would check a cache before reading the database. I would rate limit link creation, allow only HTTP and HTTPS destinations, and monitor latency and errors. The expected result is fast redirects for popular links and durable mappings, with replicas or partitioning added only when measurements justify the complexity."

clean: clean-logs ## Alias for clean-logs (does not remove caches or build artifacts)

clean-logs: ## Remove root .log files and .log files under logs/; preserve other files
	@rm -f -- ./*.log
	@if [ -d logs ]; then find logs -type f -name '*.log' -delete; fi

run-mock: ## Quiet interactive mock round; no telemetry or progress chatter
	@LLM_MODE=mock INTERVIEW_PREP_TELEMETRY=off $(RUN) interview_prep --log-level "$$IP_LOG_LEVEL" --no-progress

run-ollama: ## Interactive Ollama round with progress; WARNING logs, telemetry off
	@LLM_MODE=live LLM_QUESTION_GENERATOR=local LLM_ANSWER_EVALUATOR=local LLM_FEEDBACK=local INTERVIEW_PREP_TELEMETRY=off $(RUN) interview_prep --log-level "$$IP_LOG_LEVEL" --request-timeout "$$IP_TIMEOUT_SECONDS" --progress-interval "$$IP_PROGRESS_INTERVAL"

# Trace targets default to INFO; command-line IP_LOG_LEVEL overrides still take precedence.
trace-mock: IP_LOG_LEVEL = INFO
trace-mock: ## Diagnose mocks with INFO logs and console traces on stderr; requires telemetry extra
	@LLM_MODE=mock INTERVIEW_PREP_TELEMETRY=console $(RUN) interview_prep --log-level "$$IP_LOG_LEVEL"

# Trace targets default to INFO; command-line IP_LOG_LEVEL overrides still take precedence.
trace-ollama: IP_LOG_LEVEL = INFO
trace-ollama: ## Diagnose Ollama with INFO logs, progress, and traces on stderr; requires telemetry extra and local model
	@LLM_MODE=live LLM_QUESTION_GENERATOR=local LLM_ANSWER_EVALUATOR=local LLM_FEEDBACK=local INTERVIEW_PREP_TELEMETRY=console $(RUN) interview_prep --log-level "$$IP_LOG_LEVEL" --request-timeout "$$IP_TIMEOUT_SECONDS" --progress-interval "$$IP_PROGRESS_INTERVAL"

test-live-list: ## List live-provider tests without making model calls
	$(RUN) pytest integration_tests --collect-only

test-live: ## Run live OpenAI tests (may incur charges); requires the OpenAI extra and API key; refused in CI
	$(RUN) pytest integration_tests --live-models
