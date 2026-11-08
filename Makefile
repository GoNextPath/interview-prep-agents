.DEFAULT_GOAL := help

TOOL ?= uv
PYTHON ?= python3
VENV ?= .venv
FILES ?= src tests

ifeq ($(TOOL),uv)
RUN = uv run --locked python -m
else ifeq ($(TOOL),pip)
RUN = "$(VENV)/bin/python" -m
else
$(error TOOL must be uv or pip)
endif

.PHONY: help install lint test check format run smoke

help:
	@echo 'Commands (default: TOOL=uv; use TOOL=pip for pip):'
	@echo '  make install              Install project and development tools'
	@echo '  make lint                 Run Ruff checks'
	@echo '  make test                 Run pytest (TEST_ARGS="..." for selection)'
	@echo '  make check                Run lint and tests'
	@echo '  make format               Format src and tests (FILES="..." to override)'
	@echo '  make run                  Run the CLI (ARGS="..." for CLI options)'
	@echo '  make smoke                Run a non-interactive CLI example'
	@echo 'Pip setup: make install TOOL=pip PYTHON=python3.10'
	@echo 'Pip commands use VENV=.venv; no environment activation is needed.'

install:
ifeq ($(TOOL),uv)
	uv sync --locked --extra dev
else
	@test -d "$(VENV)" || $(PYTHON) -m venv "$(VENV)"
	"$(VENV)/bin/python" -m pip install -e ".[dev]"
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
