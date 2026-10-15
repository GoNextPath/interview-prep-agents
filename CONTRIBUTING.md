# Contributing

Thanks for helping! Contributing is optional and self-paced. Most building happens between study group sessions.

## Getting set up

```bash
git clone https://github.com/GoNextPath/interview-prep-agents.git
cd interview-prep-agents
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## How we work

1. **Pick up an issue** for your area (see [docs/teams.md](docs/teams.md)), or open one describing what you plan to do.
2. **Branch** from `main`: `git checkout -b <area>/<short-description>`, e.g. `evaluator/rubric-v1`.
3. **Keep PRs small** and focused on one thing. Add or update tests.
4. **Run checks** before pushing: `ruff check . && pytest`.
5. **Open a PR**, fill in the template, and ask someone from your team to review. Changes to `src/interview_prep/models.py` need a reviewer from each affected team.

## Ground rules

- **Never commit secrets.** API keys go in `.env`, which git ignores. Copy `.env.example` to get started.
- **Treat model output and user answers as untrusted.** See [SECURITY.md](SECURITY.md).
- **Keep docs readable.** If your change affects how someone runs or uses the project, update the README.
- **Watch costs.** Use small or cheap models while developing, and mock LLM calls in tests.

## AI-assisted contributions

We haven't set a policy yet (it's in [docs/decisions.md](docs/decisions.md)). Until we do: you may use AI tools, but you must understand and be able to explain every line you submit, and please say in the PR description if AI wrote a significant part of it.

## Getting credit

Every merged PR shows up in the repo's contributor history under your GitHub account, so use the account you want on your portfolio.
