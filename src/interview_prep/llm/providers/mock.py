"""Deterministic, input-aware development fixtures preserving the scaffold behavior."""

from interview_prep.llm.contracts import ModelError, Request
from interview_prep.llm.telemetry import record_response_model


class MockClient:
    def generate(self, request: Request) -> dict:
        record_response_model("fixture")
        data = request.data
        if request.task == "question_generator":
            return {
                "prompt": f"[stub] Tell me about a time you worked with {data['topic']}.",
                "expected_points": ["situation", "action", "result"],
            }
        if request.task == "answer_evaluator":
            criteria = [
                {
                    "criterion": point,
                    "score": float(point.lower() in data["answer"].lower()),
                    "rationale": "[stub] keyword match",
                }
                for point in data["expected_points"]
            ]
            return {"criteria": criteria}
        if request.task == "feedback":
            return {
                "summary": f"[stub] Overall score: {data['overall_score']:.0%}",
                "strengths": [
                    f"You covered {c['criterion']}." for c in data["criteria"] if c["score"] >= 0.5
                ],
                "improvements": [
                    f"Try to address {c['criterion']}." for c in data["criteria"] if c["score"] < 0.5
                ],
            }
        raise ModelError(f"No mock fixture for task {request.task!r}")
