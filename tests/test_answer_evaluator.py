"""Tests for answer evaluator."""

import pytest

from interview_prep.agents import AnswerEvaluator
from interview_prep.models import Answer, Difficulty, Question


def _q():
    return Question(id="q1", topic="t", difficulty=Difficulty.EASY, prompt="p", expected_points=["result"])


def test_score_is_between_0_and_1():
    e = AnswerEvaluator().evaluate(_q(), Answer(question_id="q1", text="the result was good"))
    assert 0.0 <= e.overall_score <= 1.0
    assert len(e.criteria) == 1


@pytest.mark.parametrize("scores", [[], [0, 0, 0], [0.2, 0.6, 1.0]])
def test_overall_score_is_mean_of_criteria(scores):
    points = [f"point-{i}" for i in range(len(scores))]

    class Client:
        def generate(self, request):
            return {
                "criteria": [
                    {"criterion": point, "score": score, "rationale": "reason"}
                    for point, score in zip(points, scores)
                ]
            }

    result = AnswerEvaluator(Client()).evaluate(
        Question("q", "topic", Difficulty.EASY, "prompt", points), Answer("q", "a")
    )
    assert result.overall_score == (sum(scores) / len(scores) if scores else 0)
