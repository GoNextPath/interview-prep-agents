"""Metrics Agent: logs outcomes and feeds new test cases back to the Question Generator.

Team: see docs/teams.md
TODO: logging schema and storage, aggregation logic, test-case generation loop.
"""

from __future__ import annotations

from collections import defaultdict

from interview_prep.models import Outcome, Question


class MetricsAgent:
    def __init__(self) -> None:
        # Stub: in memory only. Replace with real storage.
        self.outcomes: list[Outcome] = []

    def record(self, outcome: Outcome) -> None:
        self.outcomes.append(outcome)

    def average_score_by_topic(self) -> dict[str, float]:
        totals: dict[str, list[float]] = defaultdict(list)
        for o in self.outcomes:
            totals[o.question.topic].append(o.evaluation.overall_score)
        return {topic: sum(s) / len(s) for topic, s in totals.items()}

    def new_test_cases(self, threshold: float = 0.5) -> list[Question]:
        """Questions people struggled with, to send back to the Question Generator."""
        return [o.question for o in self.outcomes if o.evaluation.overall_score < threshold]
