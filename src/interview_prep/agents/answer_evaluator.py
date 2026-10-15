"""Answer Evaluator: scores a practice answer against a rubric.

Team: see docs/teams.md
TODO: rubric design, scoring logic, prompt templates, LLM call.

Security note: the answer text is untrusted user input. Never let it
override the rubric or the scoring instructions (see SECURITY.md).
"""

from __future__ import annotations

from interview_prep.models import Answer, CriterionScore, Evaluation, Question


class AnswerEvaluator:
    def evaluate(self, question: Question, answer: Answer) -> Evaluation:
        # Stub: give each expected point full credit if it's mentioned.
        criteria = [
            CriterionScore(
                criterion=point,
                score=1.0 if point.lower() in answer.text.lower() else 0.0,
                rationale="[stub] keyword match",
            )
            for point in question.expected_points
        ]
        overall = sum(c.score for c in criteria) / len(criteria) if criteria else 0.0
        return Evaluation(question_id=question.id, overall_score=overall, criteria=criteria)
