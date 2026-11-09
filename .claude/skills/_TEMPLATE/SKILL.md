---
name: add-a-thing
description: Use when someone wants to <do the thing> in <this part of the pipeline>. Covers <what it walks them through>.
---

# Add a thing

<One or two sentences: what this skill helps someone do, and why it's fiddly enough
to be worth writing down.>

## Before you start

- <What has to exist already - a file, a decision, a passing test suite.>
- <Anything the person needs to have decided before touching code.>

## Steps

1. <First step. Name the real file path.>
2. <Second step.>
3. <Keep going. Short imperative steps, not prose.>

## Checks

- `make check` passes (lint and tests)
- <Anything specific to this change - a new test, a fixture, a schema that has to stay valid.>

## Gotchas

- <The thing that trips people up. This is usually the most valuable section.>

## Not yet decided

- <Anything this skill assumes but the project hasn't settled. Link the issue.>

<!--
Writing notes - delete this comment before you commit.

- The description is the most important line. It's how the agent decides whether this
  skill applies. Say WHEN to use it, not just what it is.
- Keep the whole thing short. Twenty lines is fine. Length has a cost: the body gets
  loaded into context whenever the skill is relevant.
- Write for the pipeline we're building, not the one we have. Where a step doesn't
  exist yet, put it under 'Not yet decided' and open an issue rather than inventing it.
- Reference real paths so someone can check your instructions against the repo.
-->
