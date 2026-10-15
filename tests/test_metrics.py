from interview_prep.pipeline import Pipeline


def test_average_score_by_topic():
    p = Pipeline()
    p.submit(p.ask("a"), "situation action result")
    p.submit(p.ask("a"), "nothing")
    assert p.metrics.average_score_by_topic()["a"] == 0.5
