"""Feedback Agent: turns a score into specific, actionable feedback.

Team: see docs/teams.md
TODO: feedback templates, tone and specificity tuning, LLM call.
"""

from __future__ import annotations

from interview_prep.models import Evaluation, Feedback, Question


class FeedbackAgent:
    def give_feedback(self, question: Question, evaluation: Evaluation) -> Feedback:
        # Stub: replace with a real implementation.
        strengths = [c.criterion for c in evaluation.criteria if c.score >= 0.5]
        improvements = [c.criterion for c in evaluation.criteria if c.score < 0.5]
        return Feedback(
            question_id=question.id,
            summary=f"[stub] Overall score: {evaluation.overall_score:.0%}",
            strengths=[f"You covered {s}." for s in strengths],
            improvements=[f"Try to address {i}." for i in improvements],
        )
