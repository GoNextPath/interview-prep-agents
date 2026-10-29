# Use the project's virtual environment when present; override with PYTHON=/path/to/python.
PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
IP_LOG_LEVEL ?= WARNING
IP_TIMEOUT_SECONDS ?= 120
IP_PROGRESS_INTERVAL ?= 10
export IP_LOG_LEVEL IP_TIMEOUT_SECONDS IP_PROGRESS_INTERVAL

.DEFAULT_GOAL := help
.PHONY: help test lint check clean clean-logs run-mock run-ollama trace-mock trace-ollama test-live-list test-live

help: ## List available development commands (the default target)
	@awk 'BEGIN {printf "Usage: make <target> [PYTHON=/path/to/python] [IP_LOG_LEVEL=WARNING]\n\n"} /^[a-zA-Z0-9_-]+:.*## / {split($$0, parts, ":.*## "); printf "  %-18s %s\n", parts[1], parts[2]}' $(MAKEFILE_LIST)

test: ## Run offline tests; no model credentials or network access needed
	"$(PYTHON)" -m pytest tests

lint: ## Check Python code with Ruff
	"$(PYTHON)" -m ruff check .

check: lint test ## Run lint and offline tests

clean: clean-logs ## Alias for clean-logs (does not remove caches or build artifacts)

clean-logs: ## Remove root .log files and .log files under logs/; preserve other files
	@rm -f -- ./*.log
	@if [ -d logs ]; then find logs -type f -name '*.log' -delete; fi

# Trace targets default to INFO; command-line IP_LOG_LEVEL overrides still take precedence.
trace-mock trace-ollama: IP_LOG_LEVEL = INFO

run-mock: ## Quiet interactive mock round; no telemetry or progress chatter
	@LLM_MODE=mock INTERVIEW_PREP_TELEMETRY=off "$(PYTHON)" -m interview_prep --log-level "$$IP_LOG_LEVEL" --no-progress

run-ollama: ## Interactive Ollama round with progress; WARNING logs, telemetry off
	@LLM_MODE=live LLM_QUESTION_GENERATOR=local LLM_ANSWER_EVALUATOR=local LLM_FEEDBACK=local INTERVIEW_PREP_TELEMETRY=off "$(PYTHON)" -m interview_prep --log-level "$$IP_LOG_LEVEL" --request-timeout "$$IP_TIMEOUT_SECONDS" --progress-interval "$$IP_PROGRESS_INTERVAL"

trace-mock: ## Diagnose mocks with INFO logs and console traces on stderr; requires telemetry extra
	@LLM_MODE=mock INTERVIEW_PREP_TELEMETRY=console "$(PYTHON)" -m interview_prep --log-level "$$IP_LOG_LEVEL"

trace-ollama: ## Diagnose Ollama with INFO logs, progress, and traces on stderr; requires telemetry extra and local model
	@LLM_MODE=live LLM_QUESTION_GENERATOR=local LLM_ANSWER_EVALUATOR=local LLM_FEEDBACK=local INTERVIEW_PREP_TELEMETRY=console "$(PYTHON)" -m interview_prep --log-level "$$IP_LOG_LEVEL" --request-timeout "$$IP_TIMEOUT_SECONDS" --progress-interval "$$IP_PROGRESS_INTERVAL"

test-live-list: ## List live-provider tests without making model calls
	"$(PYTHON)" -m pytest integration_tests --collect-only

test-live: ## Run live OpenAI tests (may incur charges); requires the OpenAI extra and API key; refused in CI
	"$(PYTHON)" -m pytest integration_tests --live-models
