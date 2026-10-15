from interview_prep.models import Difficulty
from interview_prep.pipeline import Pipeline


def test_full_round_runs():
    p = Pipeline()
    q = p.ask("teamwork", Difficulty.EASY)
    outcome = p.submit(q, "The situation was tense; my action was to listen; the result was a shipped feature.")
    assert 0.0 <= outcome.evaluation.overall_score <= 1.0
    assert outcome.feedback.summary
    assert len(p.metrics.outcomes) == 1


def test_weak_answers_feed_back_to_generator():
    p = Pipeline()
    q = p.ask("teamwork")
    p.submit(q, "I don't know.")
    assert p.close_loop() == 1
    assert p.generator.seed_cases == [q]
