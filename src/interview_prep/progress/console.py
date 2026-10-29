"""Console rendering helpers, separate from the client and command-line parser."""

import sys

from interview_prep.progress.events import ProgressEvent


def print_progress(event: ProgressEvent) -> None:
    label = {
        "question_generator": "Generating question",
        "answer_evaluator": "Evaluating answer",
        "feedback": "Preparing feedback",
    }.get(event.agent, event.agent)
    detail = {
        "started": "started",
        "waiting": "still waiting",
        "completed": "model response received",
        "failed": "failed",
    }[event.phase]
    print(
        f"[{event.provider}/{event.model}] {label}: {detail} ({event.elapsed_seconds:.0f}s elapsed)",
        file=sys.stderr,
        flush=True,
    )
