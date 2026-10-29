"""Real OpenAI smoke test. Excluded from ordinary pytest collection."""

import os

from interview_prep.agents import QuestionGenerator
from interview_prep.llm import close_client, create_client
from interview_prep.models import Difficulty


def test_live_openai_question():
    client = create_client(
        "question_generator",
        env={
            "LLM_MODE": "live",
            "LLM_QUESTION_GENERATOR": "openai-fast",
            "OPENAI_API_KEY": os.environ["OPENAI_API_KEY"],
        },
    )
    try:
        assert QuestionGenerator(client).generate("databases", Difficulty.EASY).prompt
    finally:
        close_client(client)
