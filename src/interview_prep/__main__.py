"""Minimal CLI: run one question through the whole pipeline.

python -m interview_prep --topic "system design" --difficulty medium
"""

from __future__ import annotations

import argparse
import sys

from interview_prep.models import Difficulty
from interview_prep.pipeline import Pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Practice one interview question.")
    parser.add_argument("--topic", default="teamwork")
    parser.add_argument("--difficulty", choices=[d.value for d in Difficulty], default="medium")
    parser.add_argument("--answer", help="Answer text. If omitted, you'll be prompted.")
    args = parser.parse_args()

    pipeline = Pipeline()
    question = pipeline.ask(args.topic, Difficulty(args.difficulty))
    print(f"\nQ: {question.prompt}\n")
    if args.answer is not None:
        answer = args.answer
    else:
        try:
            answer = input("Your answer: ")
        except EOFError:
            answer = ""
        except KeyboardInterrupt:
            # Ctrl-C at the prompt: exit quietly with the conventional SIGINT status, no traceback.
            print("\nCancelled.", file=sys.stderr)
            sys.exit(130)

    if not answer.strip():
        print('No answer given. Type an answer at the prompt or pass --answer "...".\n', file=sys.stderr)
        parser.print_help(sys.stderr)
        parser.exit(2)

    outcome = pipeline.submit(question, answer)
    fb = outcome.feedback
    print(f"\n{fb.summary}")
    for s in fb.strengths:
        print(f"  + {s}")
    for i in fb.improvements:
        print(f"  - {i}")


if __name__ == "__main__":
    main()
