# Contributing

Thanks for helping! Contributing is optional and self-paced. Most building happens between study group sessions.

You don't need write access to this repo or membership in the GoNextPath org. Contributions come in as pull requests from your own fork.

## Getting set up

Fork this repo first - use the Fork button at the top right of the repo page. You'll get your own copy at https://github.com/<your-username>/interview-prep-agents

Then clone your fork and set up the environment:

```bash
git clone https://github.com/<your-username>/interview-prep-agents.git
cd interview-prep-agents
git remote add upstream https://github.com/GoNextPath/interview-prep-agents.git
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

`origin` is your fork, which is where you push. `upstream` is this repo, which is where pull requests go.

## How we work

1. **Pick up an issue** for your area (see [docs/teams.md](docs/teams.md)), or open one describing what you plan to do.
2. **Sync your fork** before you start: `git checkout main && git pull upstream main`.
3. **Branch** from `main`: `git checkout -b <area>/<short-description>`, e.g. `evaluator/rubric-v1`.
4. **Keep PRs small** and focused on one thing. Add or update tests.
5. **Run checks** before pushing: `ruff check . && pytest`.
6. **Push to your fork**: `git push origin <branch-name>`. Over HTTPS, GitHub asks for a personal access token instead of your password. Create a fine-grained token (GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens) with **Only select repositories** set to your fork and **Contents: Read and write**. With read-only access, the push fails with `403`.
7. **Open a PR** against `GoNextPath/interview-prep-agents`, fill in the template, and ask someone from your team to review. Changes to `src/interview_prep/models.py` need a reviewer from each affected team.

After you push, GitHub usually shows a "Compare & pull request" banner on your fork. That is the quickest way to open the PR.

## Keeping your fork up to date

```bash
git checkout main
git pull upstream main
git push origin main
```

Worth doing before each new branch so you are not building against stale code.

## Ground rules

- **Never commit secrets.** API keys go in `.env`, which git ignores. Copy `.env.example` to get started.
- **Treat model output and user answers as untrusted.** See [SECURITY.md](SECURITY.md).
- **Keep docs readable.** If your change affects how someone runs or uses the project, update the README.
- **Watch costs.** Use small or cheap models while developing, and mock LLM calls in tests.

## AI-assisted contributions

We haven't set a policy yet (it's in [docs/decisions.md](docs/decisions.md)). Until we do: you may use AI tools, but you must understand and be able to explain every line you submit, and please say in the PR description if AI wrote a significant part of it.

## Getting credit

Every merged PR shows up in the repo's contributor history under your GitHub account, so use the account you want on your portfolio. A pull request from your fork counts exactly the same as one opened from a branch here.
