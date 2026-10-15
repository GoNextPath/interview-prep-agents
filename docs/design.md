# Design doc (draft)

> Template to fill in. Keep it short: one page is plenty.

## Problem statement

_What problem does this solve, and for whom?_

## Goals

-

## Non-goals

-

## MVP

_The smallest version that runs end to end and is useful._

- [ ] Question Generator returns a question for a given topic and difficulty
- [ ] Answer Evaluator scores an answer against a rubric
- [ ] Feedback Agent turns the score into feedback
- [ ] Metrics Agent logs the outcome
- [ ] CLI runs a full practice round

## Milestones

| Milestone | Target date | Definition of done |
|---|---|---|
| M1: Pipeline runs with stubs | | `python -m interview_prep` works; CI is green |
| M2: MVP | | |
| M3: | | |

## Architecture

See the diagram in the [README](../README.md). The agents talk only through the types in `src/interview_prep/models.py`.

## Risks

- Prompt injection through candidate answers
- LLM cost
- Evaluation quality (how do we know a score is good?)
