"""Wires the four agents together into one practice round."""

from __future__ import annotations

from interview_prep.agents import AnswerEvaluator, FeedbackAgent, MetricsAgent, QuestionGenerator
from interview_prep.models import Answer, Difficulty, Outcome, Question


class Pipeline:
    def __init__(self) -> None:
        self.generator = QuestionGenerator()
        self.evaluator = AnswerEvaluator()
        self.feedback = FeedbackAgent()
        self.metrics = MetricsAgent()

    def ask(self, topic: str, difficulty: Difficulty = Difficulty.MEDIUM) -> Question:
        return self.generator.generate(topic, difficulty)

    def submit(self, question: Question, answer_text: str) -> Outcome:
        answer = Answer(question_id=question.id, text=answer_text)
        evaluation = self.evaluator.evaluate(question, answer)
        feedback = self.feedback.give_feedback(question, evaluation)
        outcome = Outcome(question=question, answer=answer, evaluation=evaluation, feedback=feedback)
        self.metrics.record(outcome)
        return outcome

    def close_loop(self) -> int:
        """Feed weak spots back to the Question Generator. Returns how many were added."""
        cases = self.metrics.new_test_cases()
        self.generator.add_test_cases(cases)
        return len(cases)
