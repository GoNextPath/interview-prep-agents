from interview_prep.agents import FeedbackAgent
from interview_prep.models import CriterionScore, Difficulty, Evaluation, Question


def test_low_scores_become_improvements():
    q = Question(id="q1", topic="t", difficulty=Difficulty.EASY, prompt="p")
    ev = Evaluation(question_id="q1", overall_score=0.0, criteria=[CriterionScore("result", 0.0)])
    fb = FeedbackAgent().give_feedback(q, ev)
    assert fb.improvements and not fb.strengths
