# Decisions and open questions

When a question gets settled, move it to **Decided** with the date and a one-line reason.

## Open

- **Scope / design doc:** write a short design doc with a problem statement, goals, a simple MVP and milestones. *(Pronita, Laurie, Chen)* Use the template in [`design.md`](design.md).
- **Security:** prompt injection, compromised models, sensitive assets, package audits. This matters because the project is open source and uses AI. *(Shannon)* Starting point: [SECURITY.md](../SECURITY.md).
- **AI-written PRs:** do we accept and review PRs written by AI tools? If so, what disclosure do we require? *(Laurie)*
- **Frontend:** its own team, or part of Infra?
- **Model provider and cost:** which LLM API(s) to use, and how to keep costs under control. *(Angelica)*
- **Milestones:** set the deliverable milestones. *(Chen)*

## Decided

- Public repo in the GoNextPath GitHub org, MIT license.
- Python 3.10+, with `pytest` for tests and `ruff` for linting (easy to revisit).
