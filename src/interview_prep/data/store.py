"""Load seed questions and labelled answers from JSON files.

The default directory is the repository ``data/`` folder. ``label`` stays
separate from ``Answer.text``. See ``open_questions.md`` for scoring
decisions this seed set does not settle.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from interview_prep.models import Answer, CriterionScore, Difficulty, Evaluation, Question

# store.py -> data -> interview_prep -> src -> repository root
_DEFAULT_DATA_DIR = Path(__file__).resolve().parents[3] / "data"
_OVERALL_TOLERANCE = 0.01


@dataclass(frozen=True)
class LabelledAnswer:
    """A practice answer plus the hand label used to check the evaluator.

    ``label`` is not part of ``answer.text``.
    """

    id: str
    answer: Answer
    label: Evaluation


class JsonSeedStore:
    """Read-only seed bank backed by ``questions.json`` and ``answers.json``."""

    def __init__(self, data_dir: Path | None = None) -> None:
        self.data_dir = Path(data_dir) if data_dir is not None else _DEFAULT_DATA_DIR
        self._questions = _load_questions(self.data_dir / "questions.json")
        self._answers = _load_answers(self.data_dir / "answers.json", self._questions)

    def questions(self) -> list[Question]:
        """Return every seed question, in file order."""
        return list(self._questions.values())

    def question(self, question_id: str) -> Question:
        """Return one question. Raises ``KeyError`` when the id is unknown."""
        try:
            return self._questions[question_id]
        except KeyError:
            raise KeyError(f"unknown question id: {question_id}") from None

    def answers(self) -> list[LabelledAnswer]:
        """Return every labelled answer, in file order."""
        return list(self._answers)

    def answers_for(self, question_id: str) -> list[LabelledAnswer]:
        """Return labelled answers for one question. Raises ``KeyError`` when the id is unknown."""
        self.question(question_id)
        return [item for item in self._answers if item.answer.question_id == question_id]


def _load_json(path: Path) -> dict:
    if not path.is_file():
        raise ValueError(f"missing seed file: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path.name}: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise TypeError(f"{path.name} must be a JSON object")
    return payload


def _require_str(record: dict, field: str, record_id: str) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{record_id} field {field} must be a non-empty string")
    return value


def _require_score(value: object, record_id: str, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{record_id} {field} must be a number from 0.0 to 1.0")
    score = float(value)
    if not 0.0 <= score <= 1.0:
        raise ValueError(f"{record_id} {field} must be from 0.0 to 1.0")
    return score


def _load_questions(path: Path) -> dict[str, Question]:
    payload = _load_json(path)
    records = payload.get("questions")
    if not isinstance(records, list):
        raise TypeError(f"{path.name} field questions must be a list")
    questions: dict[str, Question] = {}
    for index, record in enumerate(records):
        record_id = f"{path.name}[{index}]"
        if not isinstance(record, dict):
            raise TypeError(f"{record_id} must be an object")
        question_id = _require_str(record, "id", record_id)
        if question_id in questions:
            raise ValueError(f"duplicate question id: {question_id}")
        difficulty_value = record.get("difficulty")
        if not isinstance(difficulty_value, str):
            raise TypeError(f"{question_id} difficulty must be easy, medium, or hard")
        try:
            difficulty = Difficulty(difficulty_value)
        except ValueError:
            raise ValueError(f"{question_id} difficulty must be easy, medium, or hard") from None
        points = record.get("expected_points")
        if (
            not isinstance(points, list)
            or not points
            or not all(isinstance(point, str) and point.strip() for point in points)
        ):
            raise ValueError(f"{question_id} expected_points must be a non-empty list of strings")
        if len(points) != len(set(points)):
            raise ValueError(f"{question_id} expected_points must be unique")
        questions[question_id] = Question(
            id=question_id,
            topic=_require_str(record, "topic", question_id),
            difficulty=difficulty,
            prompt=_require_str(record, "prompt", question_id),
            expected_points=list(points),
        )
    return questions


def _load_answers(path: Path, questions: dict[str, Question]) -> list[LabelledAnswer]:
    payload = _load_json(path)
    records = payload.get("answers")
    if not isinstance(records, list):
        raise TypeError(f"{path.name} field answers must be a list")
    answers: list[LabelledAnswer] = []
    seen: set[str] = set()
    for index, record in enumerate(records):
        record_id = f"{path.name}[{index}]"
        if not isinstance(record, dict):
            raise TypeError(f"{record_id} must be an object")
        answer_id = _require_str(record, "id", record_id)
        if answer_id in seen:
            raise ValueError(f"duplicate answer id: {answer_id}")
        seen.add(answer_id)
        question_id = _require_str(record, "question_id", answer_id)
        question = questions.get(question_id)
        if question is None:
            raise ValueError(f"{answer_id} question_id does not match a seed question: {question_id}")
        label = _load_label(record.get("label"), answer_id, question)
        answers.append(
            LabelledAnswer(
                id=answer_id,
                answer=Answer(question_id=question_id, text=_require_str(record, "text", answer_id)),
                label=label,
            )
        )
    return answers


def _load_label(raw: object, answer_id: str, question: Question) -> Evaluation:
    if not isinstance(raw, dict):
        raise TypeError(f"{answer_id} label must be an object")
    criteria_raw = raw.get("criteria")
    if not isinstance(criteria_raw, list):
        raise TypeError(f"{answer_id} label.criteria must be a list")
    expected = question.expected_points
    if len(criteria_raw) != len(expected):
        raise ValueError(f"{answer_id} label.criteria must have one score per expected point")
    criteria: list[CriterionScore] = []
    for point, item in zip(expected, criteria_raw):
        if not isinstance(item, dict):
            raise TypeError(f"{answer_id} criterion {point!r} must be an object")
        criterion = item.get("criterion")
        if criterion != point:
            raise ValueError(f"{answer_id} criteria must follow expected_points; found {criterion!r}")
        rationale = item.get("rationale", "")
        if not isinstance(rationale, str):
            raise TypeError(f"{answer_id} rationale for {point!r} must be a string")
        criteria.append(
            CriterionScore(
                criterion=point,
                score=_require_score(item.get("score"), answer_id, f"score for {point!r}"),
                rationale=rationale,
            )
        )
    overall = _require_score(raw.get("overall_score"), answer_id, "overall_score")
    mean = sum(item.score for item in criteria) / len(criteria)
    if abs(overall - mean) > _OVERALL_TOLERANCE:
        raise ValueError(f"{answer_id} overall_score must be the mean of its criterion scores")
    return Evaluation(question_id=question.id, overall_score=overall, criteria=criteria)
