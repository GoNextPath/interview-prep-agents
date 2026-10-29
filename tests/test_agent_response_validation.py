"""Tests for agent response validation."""

import pytest

from interview_prep.agents import AnswerEvaluator, FeedbackAgent, QuestionGenerator
from interview_prep.llm import ModelError
from interview_prep.models import Answer, Difficulty, Evaluation, Question


@pytest.mark.parametrize(
    "result",
    [
        {},
        {"prompt": "", "expected_points": []},
        {"prompt": "ok", "expected_points": "wrong"},
    ],
)
def test_generator_rejects_invalid_output(result):
    class InvalidClient:
        def generate(self, request):
            return result

    with pytest.raises(ModelError):
        QuestionGenerator(InvalidClient()).generate("topic", Difficulty.EASY)


@pytest.mark.parametrize("score", [-1, 2, float("nan"), float("inf"), True, "0.5"])
def test_evaluator_rejects_invalid_scores(score):
    class InvalidClient:
        def generate(self, request):
            return {"criteria": [{"criterion": "point", "score": score, "rationale": "reason"}]}

    with pytest.raises(ModelError):
        AnswerEvaluator(InvalidClient()).evaluate(
            Question("q", "topic", Difficulty.EASY, "prompt", ["point"]), Answer("q", "a")
        )


def test_feedback_rejects_invalid_output():
    class InvalidClient:
        def generate(self, request):
            return {"summary": "ok", "strengths": [None], "improvements": []}

    with pytest.raises(ModelError):
        FeedbackAgent(InvalidClient()).give_feedback(
            Question("q", "topic", Difficulty.EASY, "prompt"),
            Evaluation("q", 0.5),
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("criterion", None),
        ("criterion", " "),
        ("rationale", ""),
        ("rationale", {"PRIVATE": "PRIVATE"}),
        ("score", "PRIVATE"),
    ],
)
def test_evaluator_validation_names_field_and_index_without_values(field, value):
    class InvalidClient:
        def generate(self, request):
            invalid = {"criterion": "second", "score": 1.0, "rationale": "reason"}
            invalid[field] = value
            return {"criteria": [{"criterion": "first", "score": 1.0, "rationale": "reason"}, invalid]}

    question = Question("q", "topic", Difficulty.EASY, "prompt", ["first", "second"])
    with pytest.raises(ModelError) as result:
        AnswerEvaluator(InvalidClient()).evaluate(question, Answer("q", "PRIVATE-ANSWER"))
    assert f"answer_evaluator.criteria[1].{field}:" in str(result.value)
    assert "PRIVATE" not in str(result.value)
