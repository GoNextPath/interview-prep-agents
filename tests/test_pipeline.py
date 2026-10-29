"""Tests for pipeline."""

import pytest

from interview_prep.llm import ConfigurationError
from interview_prep.llm.registry import AGENTS
from interview_prep.models import Difficulty
from interview_prep.pipeline import Pipeline


def test_full_round_runs():
    p = Pipeline()
    q = p.ask("teamwork", Difficulty.EASY)
    outcome = p.submit(
        q, "The situation was tense; my action was to listen; the result was a shipped feature."
    )
    assert 0.0 <= outcome.evaluation.overall_score <= 1.0
    assert outcome.feedback.summary
    assert len(p.metrics.outcomes) == 1


def test_weak_answers_feed_back_to_generator():
    p = Pipeline()
    q = p.ask("teamwork")
    p.submit(q, "I don't know.")
    assert p.close_loop() == 1
    assert p.generator.seed_cases == [q]


def test_dependency_injection_overrides_environment(monkeypatch):
    class FixedClient:
        def generate(self, request):
            assert request.task == "question_generator"
            return {"prompt": "Injected question", "expected_points": ["index"]}

    monkeypatch.setenv("LLM_MODE", "live")
    monkeypatch.setenv("LLM_QUESTION_GENERATOR", "missing")
    pipeline = Pipeline(clients={"question_generator": FixedClient()})
    question = pipeline.ask("databases")
    assert question.prompt == "Injected question"
    assert pipeline.submit(question, "index").evaluation.overall_score == 1
    assert pipeline.metrics.average_score_by_topic() == {"databases": 1}


def test_pipeline_closes_owned_clients_and_not_injected_clients(monkeypatch):
    owned = []

    class Client:
        def __init__(self):
            self.closed = 0

        def close(self):
            self.closed += 1

    def create(*args, **kwargs):
        client = Client()
        owned.append(client)
        return client

    monkeypatch.setattr("interview_prep.pipeline.create_client", create)
    injected = Client()
    with Pipeline(clients={"feedback": injected}) as pipeline:
        assert len(owned) == 2
    pipeline.close()
    assert [client.closed for client in owned] == [1, 1]
    assert injected.closed == 0


def test_partial_pipeline_construction_closes_created_clients(monkeypatch):
    closed = []

    class Client:
        def close(self):
            closed.append(True)

    def create(agent, **kwargs):
        if agent == AGENTS[1]:
            raise ConfigurationError("missing key")
        return Client()

    monkeypatch.setattr("interview_prep.pipeline.create_client", create)
    with pytest.raises(ConfigurationError):
        Pipeline()
    assert closed == [True]


def test_unknown_injected_agent_is_a_configuration_error():
    with pytest.raises(ConfigurationError, match="Unknown client agents"):
        Pipeline(clients={"unknown": object()})
