"""awrena CLI — run head-to-head matches and judge the results.

Exit codes: 0 success (verdict returned), 1 error (could not judge), 2 critical
error (invalid input).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .engine import ContentLengthCriterion, Judge, LengthCriterion


def load_responses(responses_file: str) -> tuple[str, str, str]:
    """Load agent responses from a JSON file.

    Expected format:
    {
      "question": "optional context",
      "a_response": "output from agent A",
      "b_response": "output from agent B"
    }

    Args:
        responses_file: Path to JSON file

    Returns:
        (question, a_response, b_response)

    Raises:
        ValueError: If file is invalid or missing required fields
    """
    try:
        data = json.loads(Path(responses_file).read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"responses file not found: {responses_file}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {responses_file}: {exc}") from exc

    question = data.get("question", "")
    a_response = data.get("a_response", "")
    b_response = data.get("b_response", "")

    if not isinstance(a_response, str) or not isinstance(b_response, str):
        raise ValueError("a_response and b_response must be strings")

    return question, a_response, b_response


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the awrena CLI."""
    # GENERATED doctor intercept (gen_aw_doctor.py) -- do not edit
    _dv = locals().get("argv")
    if (_dv if _dv is not None else __import__("sys").argv[1:])[:1] == ["doctor"]:
        from ._doctor import report
        return report()
    # Handle --self-test flag before parsing subcommands (argparse can't handle
    # subcommand names starting with dashes)
    if argv is None:
        argv = sys.argv[1:]
    if "--self-test" in argv:
        return _self_test()

    ap = argparse.ArgumentParser(
        prog="awrena",
        description="Run one judged head-to-head between two agents and read the scored verdict."
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    # judge subcommand
    judge_parser = sub.add_parser("judge", help="Run a head-to-head match and judge the results")
    judge_parser.add_argument(
        "responses",
        help="JSON file with a_response, b_response, and optional question"
    )
    judge_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="output format (default: text)"
    )
    judge_parser.add_argument(
        "--criteria",
        choices=["default", "length", "content"],
        default="default",
        help="scoring criteria to use (default: length)"
    )

    args = ap.parse_args(argv)

    # Handle judge subcommand
    if args.cmd == "judge":
        try:
            question, a_response, b_response = load_responses(args.responses)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2

        # Select criteria
        criteria_list = []
        if args.criteria == "default":
            criteria_list = [LengthCriterion()]
        elif args.criteria == "length":
            criteria_list = [LengthCriterion()]
        elif args.criteria == "content":
            criteria_list = [ContentLengthCriterion()]

        # Run judgment
        judge = Judge(criteria_list)
        verdict = judge.judge(a_response, b_response, question)

        if not verdict.is_valid():
            print(f"ERROR: {verdict.error}", file=sys.stderr)
            return 1

        # Output
        if args.format == "json":
            output = {
                "winner": verdict.winner,
                "a_score": verdict.a_score,
                "b_score": verdict.b_score,
                "reason": verdict.reason,
            }
            print(json.dumps(output, indent=2))
        else:
            print(verdict.summary())

        return 0

    return 2


def _self_test() -> int:
    """Self-test that exercises the real judging logic offline.

    Returns 0 if all tests pass, 1 if any fail.
    """
    from .engine import Judge, LengthCriterion

    failed = False

    # Test 1: both empty should tie
    judge = Judge([LengthCriterion()])
    verdict = judge.judge("", "", "test question")
    if verdict.winner != "tie" or verdict.error is not None:
        print(f"FAIL: both empty should tie, got {verdict.winner}")
        failed = True

    # Test 2: one empty should favor non-empty
    verdict = judge.judge("", "response B", "")
    if verdict.winner != "b" or verdict.error is not None:
        print(f"FAIL: empty vs non-empty should favor B, got {verdict.winner}")
        failed = True

    # Test 3: longer response should win
    verdict = judge.judge("short", "much longer response", "")
    if verdict.winner != "b" or verdict.error is not None:
        print(f"FAIL: longer response should win, got {verdict.winner}")
        failed = True

    # Test 4: similar length should tie
    verdict = judge.judge("same", "same", "")
    if verdict.winner != "tie" or verdict.error is not None:
        print(f"FAIL: similar length should tie, got {verdict.winner}")
        failed = True

    # Test 5: verdict is always valid (never raises)
    judge = Judge([LengthCriterion()])
    verdict = judge.judge("a" * 10000, "b" * 10000, "")
    if verdict.error is not None:
        print(f"FAIL: should not error on large inputs, got: {verdict.error}")
        failed = True

    if failed:
        print("FAIL: some self-tests failed", file=sys.stderr)
        return 1

    print("PASS: all self-tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
