# Skills

A skill is an onboarding guide for an agent. Not for a human - for the agent.

Each team owns one skill describing how to extend their part of the pipeline. Writing it
forces the design decision: you can't explain how to add a scoring criterion without
deciding what the Evaluator actually does.

## Layout

```
.claude/skills/
├── README.md              you are here
├── _TEMPLATE/
│   └── SKILL.md           copy this to start
├── add-a-question-source/ Question Generator team
├── add-a-scoring-criterion/ Answer Evaluator team
├── add-a-feedback-template/ Feedback Agent team
├── add-a-logged-metric/   Metrics Agent team
└── add-a-new-agent/       Infra team
```

Only `SKILL.md` is required. Add `references/` or `scripts/` later, if the skill outgrows
one file.

## Writing one

1. `cp -r _TEMPLATE add-a-thing` and fill it in.
2. Keep it short. Twenty lines is a reasonable first skill. The body is loaded into context
   whenever the skill is relevant, so length has a cost.
3. The `description` is the most important line you'll write - it's how the agent decides
   whether the skill applies at all. Say when to use it, not just what it is.
4. Write it for the pipeline we're building, not the one we have. Where a step doesn't
   exist yet, say so and open an issue. A gap you've named is more useful than one
   you've written around.

## Conventions

- Folder name is a verb phrase: `add-a-scoring-criterion`, not `scoring`.
- `name` in the frontmatter matches the folder name.
- Reference real paths in this repo (`src/interview_prep/agents/...`) so the instructions
  are checkable.
- Changes to `src/interview_prep/models.py` still need a reviewer from each affected team,
  per CONTRIBUTING. If your skill implies a change there, flag it in the PR.

## Reviewing

Review another team's skill, not your own. The question to ask: could I follow this
without asking the author anything? If not, that's the gap worth commenting on.
