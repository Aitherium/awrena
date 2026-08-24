"""awrena — run one judged head-to-head between two agents and read the scored verdict.

    from awrena import Judge

    judge = Judge()
    verdict = judge.judge(
        a_response="Agent A's output",
        b_response="Agent B's output",
        question="What was the task?"
    )

    if verdict.is_valid():
        print(f"Winner: {verdict.winner}")
        print(f"Scores: {verdict.a_score:.1f} vs {verdict.b_score:.1f}")
        print(f"Reason: {verdict.reason}")
    else:
        print(f"Error: {verdict.error}")

Part of the `aw` family. Run head-to-head comparisons between agents, get
scored verdicts, extend with custom scoring criteria.
"""

from .engine import ContentLengthCriterion, Criteria, Judge, LengthCriterion, Verdict

__version__ = "0.1.0"
__all__ = ["Judge", "Verdict", "Criteria", "LengthCriterion", "ContentLengthCriterion"]
