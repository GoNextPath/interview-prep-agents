"""Wires the four agents together into one practice round."""

from __future__ import annotations

import logging

from interview_prep.agents import AnswerEvaluator, FeedbackAgent, MetricsAgent, QuestionGenerator
from interview_prep.llm import (
    ClientOptions,
    ConfigurationError,
    LLMClient,
    ProgressCallback,
    close_client,
    create_client,
    load_registry,
)
from interview_prep.llm.registry import AGENTS, Registry
from interview_prep.models import Answer, Difficulty, Outcome, Question

logger = logging.getLogger(__name__)


class Pipeline:
    def __init__(
        self,
        *,
        clients: dict[str, LLMClient] | None = None,
        registry: Registry | None = None,
        options: ClientOptions | None = None,
        progress: ProgressCallback | None = None,
    ) -> None:
        supplied = {} if clients is None else clients
        unknown = set(supplied) - set(AGENTS)
        if unknown:
            raise ConfigurationError(f"Unknown client agents: {sorted(unknown)}")
        config = registry if registry is not None else load_registry()
        self._owned_clients: list[LLMClient] = []
        self._closed = False
        resolved = {}
        try:
            for agent in AGENTS:
                if agent in supplied:
                    resolved[agent] = supplied[agent]
                else:
                    client = create_client(agent, registry=config, options=options, progress=progress)
                    self._owned_clients.append(client)
                    resolved[agent] = client
        except BaseException:
            self.close()
            raise
        self.generator = QuestionGenerator(resolved["question_generator"])
        self.evaluator = AnswerEvaluator(resolved["answer_evaluator"])
        self.feedback = FeedbackAgent(resolved["feedback"])
        self.metrics = MetricsAgent()

    def close(self) -> None:
        if not self._closed:
            for client in reversed(self._owned_clients):
                try:
                    close_client(client)
                except Exception as exc:  # noqa: BLE001 - continue cleanup without exposing exception contents
                    logger.warning("LLM client cleanup failed error_type=%s", type(exc).__name__)
            self._closed = True

    def __enter__(self) -> Pipeline:  # noqa: PYI034 - Python 3.10 without typing_extensions dependency
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()

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
