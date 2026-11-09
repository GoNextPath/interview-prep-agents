import pytest

from interview_prep.data import JsonSeedStore
from interview_prep.models import Difficulty


def test_seed_questions_match_the_contract():
    store = JsonSeedStore()
    questions = store.questions()
    assert len(questions) == 8
    assert "teamwork" in {question.topic for question in questions}
    assert len({question.id for question in questions}) == 8
    for question in questions:
        assert question.prompt
        assert question.expected_points
        assert isinstance(question.difficulty, Difficulty)


def test_each_question_has_a_strong_and_a_weak_answer():
    store = JsonSeedStore()
    assert len(store.answers()) == 16
    for question in store.questions():
        labelled = store.answers_for(question.id)
        scores = [item.label.overall_score for item in labelled]
        assert len(scores) == 2
        assert max(scores) >= 0.5
        assert min(scores) < 0.5
        for item in labelled:
            assert item.label.question_id == question.id
            assert [criterion.criterion for criterion in item.label.criteria] == question.expected_points
            assert "overall_score" not in item.answer.text


def test_unknown_question_id_raises():
    store = JsonSeedStore()
    with pytest.raises(KeyError, match="unknown question id"):
        store.answers_for("missing")


def test_rejects_a_score_outside_the_contract(tmp_path):
    (tmp_path / "questions.json").write_text(
        """
        {"questions": [{
            "id": "q1",
            "topic": "teamwork",
            "difficulty": "easy",
            "prompt": "Tell me about a time.",
            "expected_points": ["result"]
        }]}
        """,
        encoding="utf-8",
    )
    (tmp_path / "answers.json").write_text(
        """
        {"answers": [{
            "id": "a1",
            "question_id": "q1",
            "text": "We shipped it.",
            "label": {
                "overall_score": 1.5,
                "criteria": [{"criterion": "result", "score": 1.0, "rationale": "covered"}]
            }
        }]}
        """,
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="overall_score"):
        JsonSeedStore(tmp_path)
