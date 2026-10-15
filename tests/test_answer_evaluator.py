from interview_prep.agents import AnswerEvaluator
from interview_prep.models import Answer, Difficulty, Question


def _q():
    return Question(id="q1", topic="t", difficulty=Difficulty.EASY, prompt="p", expected_points=["result"])


def test_score_is_between_0_and_1():
    e = AnswerEvaluator().evaluate(_q(), Answer(question_id="q1", text="the result was good"))
    assert 0.0 <= e.overall_score <= 1.0
    assert len(e.criteria) == 1
