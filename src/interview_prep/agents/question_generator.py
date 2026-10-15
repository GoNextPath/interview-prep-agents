"""Question Generator: creates interview questions by topic and difficulty.

Team: see docs/teams.md
TODO: topic taxonomy, difficulty calibration, prompt templates, LLM call.
"""

from __future__ import annotations

import uuid

from interview_prep.models import Difficulty, Question


class QuestionGenerator:
    def __init__(self) -> None:
        # Test cases fed back by the Metrics Agent, to be worked into future questions.
        self.seed_cases: list[Question] = []

    def generate(self, topic: str, difficulty: Difficulty) -> Question:
        # Stub: replace with a real implementation.
        return Question(
            id=str(uuid.uuid4()),
            topic=topic,
            difficulty=difficulty,
            prompt=f"[stub] Tell me about a time you worked with {topic}.",
            expected_points=["situation", "action", "result"],
        )

    def add_test_cases(self, cases: list[Question]) -> None:
        """Called by the Metrics Agent to feed new test cases back in."""
        self.seed_cases.extend(cases)
