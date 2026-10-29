"""Standalone agents release owned clients while preserving caller-owned injection."""

import pytest

from interview_prep.agents import answer_evaluator, feedback, question_generator

AGENTS = [
    (question_generator, question_generator.QuestionGenerator),
    (answer_evaluator, answer_evaluator.AnswerEvaluator),
    (feedback, feedback.FeedbackAgent),
]


class CountingClient:
    def __init__(self):
        self.close_count = 0

    def close(self):
        self.close_count += 1


@pytest.mark.parametrize("module,agent_class", AGENTS)
def test_standalone_agent_closes_its_client_once(monkeypatch, module, agent_class):
    client = CountingClient()
    monkeypatch.setattr(module, "create_client", lambda name: client)
    with agent_class() as agent:
        assert agent.client is client
        assert client.close_count == 0
    agent.close()
    assert client.close_count == 1


@pytest.mark.parametrize("module,agent_class", AGENTS)
def test_standalone_agent_closes_after_failure(monkeypatch, module, agent_class):
    client = CountingClient()
    monkeypatch.setattr(module, "create_client", lambda name: client)
    failure = RuntimeError("example failure")
    with pytest.raises(RuntimeError) as result, agent_class():
        raise failure
    assert result.value is failure
    assert client.close_count == 1


@pytest.mark.parametrize("module,agent_class", AGENTS)
def test_standalone_agent_leaves_injected_client_open(monkeypatch, module, agent_class):
    def forbidden(name):
        pytest.fail("An injected agent must not construct another client")

    monkeypatch.setattr(module, "create_client", forbidden)
    client = CountingClient()
    with agent_class(client) as agent:
        assert agent.client is client
    agent.close()
    assert client.close_count == 0
    client.close()
    assert client.close_count == 1


@pytest.mark.parametrize("module,agent_class", AGENTS)
def test_standalone_cleanup_supports_clients_without_close(monkeypatch, module, agent_class):
    class PlainClient:
        def generate(self, request):
            return {}

    monkeypatch.setattr(module, "create_client", lambda name: PlainClient())
    with agent_class() as agent:
        pass
    agent.close()
