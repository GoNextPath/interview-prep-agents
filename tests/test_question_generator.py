from interview_prep.agents import QuestionGenerator
from interview_prep.models import Difficulty


def test_generates_question_for_topic_and_difficulty():
    q = QuestionGenerator().generate("databases", Difficulty.HARD)
    assert q.topic == "databases"
    assert q.difficulty is Difficulty.HARD
    assert q.prompt
