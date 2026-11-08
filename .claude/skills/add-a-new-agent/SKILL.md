---
name: add-a-new-agent
description: Use when adding a fifth agent to the interview-prep pipeline, or when splitting an existing agent in two. Covers the file layout, the models.py contract, wiring into the pipeline, and the tests expected before review.
---

# Add a new agent

The pipeline has four agents today. Adding a fifth touches three places that are easy to
miss, which is why this is written down.

## Before you start

- The agent has one job you can say in a sentence. If it needs two, it's two agents.
- You know what it takes in and what it returns, in terms of the types in
  `src/interview_prep/models.py`.
- There's an issue for it, labelled with an `area:` label.

## Steps

1. Add `src/interview_prep/agents/<name>.py`. One class, one public method. Follow the
   shape of `answer_evaluator.py` - it's the closest thing to a reference implementation.
2. If the agent needs a type that doesn't exist, add it to `src/interview_prep/models.py`.
   Changes there need a reviewer from each affected team, per CONTRIBUTING.
3. Export it from `src/interview_prep/agents/__init__.py`.
4. Wire it into `src/interview_prep/pipeline.py` at the point in the loop where it runs.
5. Add `tests/test_<name>.py`. Mock the model call - the suite must not make network
   requests.
6. Open a PR. The labeler applies the area label from the paths you touched.

## Checks

- `uv run ruff check . && uv run pytest` passes
- The new agent has a test that fails if you delete its core logic
- `uv run python -m interview_prep` still runs end to end

## Gotchas

- **Don't reach into another agent's internals.** If you need something it computed, it
  belongs on a shared type in `models.py`. Otherwise the two agents can't be tested or
  changed independently.
- **The pipeline is a loop, not a line.** The Metrics Agent feeds back into the Question
  Generator. A new agent needs a clear answer to "what happens on the second pass?"
- **Keep the stub honest.** If the agent isn't implemented yet, return something obviously
  placeholder rather than something plausible. Plausible stubs hide missing work.

## Not yet decided

- Which model each agent calls, and how. The shared LLM client is issue #5 and has no
  owner yet - until it lands, mock the call in tests and leave a TODO in the agent.
- Where metrics are stored. Open question in `docs/decisions.md`.
