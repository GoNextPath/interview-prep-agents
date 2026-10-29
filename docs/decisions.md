# Decisions and open questions

When a question gets settled, move it to **Decided** with the date and a one-line reason.

## Open

- **Scope / design doc:** write a short design doc with a problem statement, goals, a simple MVP and milestones. *(Pronita, Laurie, Chen)* Use the template in [`design.md`](design.md).
- **Security:** prompt injection, compromised models, sensitive assets, package audits. This matters because the project is open source and uses AI. *(Shannon)* Starting point: [SECURITY.md](../SECURITY.md).
- **AI-written PRs:** do we accept and review PRs written by AI tools? If so, what disclosure do we require? *(Laurie)*
- **Frontend:** its own team, or part of Infra?
- **Model provider and cost:** which LLM API(s) to use, and how to keep costs under control. *(Angelica)* Proposed [ADR 0001](adr/0001-configurable-llm-clients.md) adds a provider-independent client and mock defaults; the team still chooses production models and budgets.
- **Milestones:** set the deliverable milestones. *(Chen)*

## Decided

- Public repo in the GoNextPath GitHub org, MIT license.
- Python 3.10+, with `pytest` for tests and `ruff` for linting (easy to revisit).
- **Contributing by fork and PR** (Oct 2026): contributors fork the repo and open PRs from their fork rather than being added to the GoNextPath org. The group is 20+ people, org seats aren't needed for this, and a PR from a fork earns the same contributor credit. Knock-on effect: CODEOWNERS isn't usable, since GitHub only auto-requests review from people with write access, so the `models.py` review rule stays a convention in CONTRIBUTING.
- **Branch protection on `main`** (Oct 2026): pull requests required, force pushes and deletions blocked, 0 required approvals for now. Worth revisiting once there are co-maintainers to review.

