"""Shared data types passed between agents.

This module is the contract between the teams. Talk to the other teams
before changing a field, since every agent depends on these types.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


@dataclass
class Question:
    id: str
    topic: str
    difficulty: Difficulty
    prompt: str
    # What a strong answer covers. The Answer Evaluator uses this to build its rubric.
    expected_points: list[str] = field(default_factory=list)


@dataclass
class Answer:
    question_id: str
    text: str


@dataclass
class CriterionScore:
    criterion: str
    score: float  # 0.0 to 1.0
    rationale: str = ""


@dataclass
class Evaluation:
    question_id: str
    overall_score: float  # 0.0 to 1.0
    criteria: list[CriterionScore] = field(default_factory=list)


@dataclass
class Feedback:
    question_id: str
    summary: str
    strengths: list[str] = field(default_factory=list)
    improvements: list[str] = field(default_factory=list)


@dataclass
class Outcome:
    """One full practice round, as recorded by the Metrics Agent."""

    question: Question
    answer: Answer
    evaluation: Evaluation
    feedback: Feedback
    recorded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
