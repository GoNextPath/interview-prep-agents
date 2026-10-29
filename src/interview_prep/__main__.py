"""Minimal CLI: run one question through the whole pipeline.

python -m interview_prep --topic "system design" --difficulty medium
"""

from __future__ import annotations

import argparse
import os
import sys
import traceback
from pathlib import Path

from interview_prep.llm import ClientOptions, ConfigurationError, ModelError, ProgressCallback, load_registry
from interview_prep.llm.options import parse_seconds
from interview_prep.llm.registry import Registry
from interview_prep.llm.telemetry import configure_logging, configure_telemetry, span
from interview_prep.models import Difficulty
from interview_prep.pipeline import Pipeline
from interview_prep.progress import print_progress


def _seconds(value: str, *, allow_zero: bool = False) -> float:
    try:
        return parse_seconds(value, name="seconds", allow_zero=allow_zero)
    except ConfigurationError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from None


def _interval(value: str) -> float:
    return _seconds(value, allow_zero=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Practice one interview question.")
    parser.add_argument("--topic", default="teamwork")
    parser.add_argument("--difficulty", choices=[d.value for d in Difficulty], default="medium")
    parser.add_argument(
        "--models-config",
        type=Path,
        help="External model registry JSON (default: packaged mock-safe registry)",
    )
    parser.add_argument(
        "--agents-config",
        type=Path,
        help="External agent assignments JSON (default: packaged, or beside --models-config)",
    )
    parser.add_argument("--answer", help="Answer text. If omitted, you'll be prompted.")
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default=None,
        help="Overrides INTERVIEW_PREP_LOG_LEVEL (default: WARNING)",
    )
    parser.add_argument(
        "--progress",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Show model-call progress (default: enabled; use --no-progress to hide)",
    )
    parser.add_argument(
        "--progress-interval",
        type=_interval,
        default=None,
        help="Seconds between waiting updates; 0 disables periodic updates",
    )
    parser.add_argument(
        "--request-timeout", type=_seconds, default=None, help="Provider network timeout in seconds"
    )
    parser.add_argument(
        "--traceback", action="store_true", help="Show diagnostic tracebacks on client errors"
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    telemetry = None
    try:
        configure_logging(args.log_level or os.environ.get("INTERVIEW_PREP_LOG_LEVEL", "WARNING"))
        telemetry = configure_telemetry(os.environ.get("INTERVIEW_PREP_TELEMETRY", "off"))
        options = ClientOptions.from_env(
            os.environ,
            timeout_seconds=args.request_timeout,
            progress_interval_seconds=args.progress_interval,
        )
        with span("interview_prep.round", {}):
            registry = load_registry(args.models_config, agents_path=args.agents_config)
            run_round(
                topic=args.topic,
                difficulty=Difficulty(args.difficulty),
                answer=args.answer,
                options=options,
                registry=registry,
                progress=print_progress if args.progress else None,
            )
    except ConfigurationError as exc:
        print(
            "\nThe practice round couldn't start. Check your configuration and diagnostic output.", flush=True
        )
        _report_error(exc, show_traceback=args.traceback)
        raise SystemExit(2) from None
    except ModelError as exc:
        print(
            "\nThe practice round couldn't be completed. Check the error details or your diagnostic log.",
            flush=True,
        )
        _report_error(exc, show_traceback=args.traceback)
        raise SystemExit(1) from None
    finally:
        if telemetry is not None:
            telemetry.shutdown()


def _report_error(error: Exception, *, show_traceback: bool) -> None:
    if show_traceback:
        traceback.print_exc()
    else:
        print(f"error: {error}", file=sys.stderr)


def run_round(
    *,
    topic: str,
    difficulty: Difficulty,
    answer: str | None,
    options: ClientOptions,
    registry: Registry,
    progress: ProgressCallback | None = None,
) -> None:
    with Pipeline(options=options, registry=registry, progress=progress) as pipeline:
        question = pipeline.ask(topic, difficulty)
        print(f"\nQ: {question.prompt}\n")
        if answer is None:
            # Print explicitly: terminal readline implementations may route input(prompt) to stderr.
            print("Your answer: ", end="", flush=True)
            answer_text = input()
        else:
            answer_text = answer

        outcome = pipeline.submit(question, answer_text)
        fb = outcome.feedback
        print(f"\n{fb.summary}")
        for s in fb.strengths:
            print(f"  + {s}")
        for i in fb.improvements:
            print(f"  - {i}")


if __name__ == "__main__":
    main()
