"""Core judging logic for head-to-head agent matches.

A Verdict compares two agent outputs and assigns scores. Every error path returns
a clear verdict rather than raising — a judge that breaks silently is worse than
one that names its failure.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Verdict:
    """The outcome of a judged head-to-head match.

    Attributes:
        winner: Name of the winning agent ("a", "b", or "tie")
        a_score: Numeric score for agent A (0-100)
        b_score: Numeric score for agent B (0-100)
        reason: Explanation of the judgment
        error: Error message if judgment could not be computed
    """
    winner: str
    a_score: float
    b_score: float
    reason: str
    error: Optional[str] = None

    def is_valid(self) -> bool:
        """True if the verdict represents a successful judgment."""
        return self.error is None

    def summary(self) -> str:
        """Human-readable summary of the verdict."""
        if self.error:
            return f"UNSCORED: {self.error}"
        score_str = f"({self.a_score:.1f} vs {self.b_score:.1f})"
        return f"{self.winner.upper()} wins {score_str}: {self.reason}"


class Criteria:
    """Scoring criteria for judging agent responses.

    A Criteria defines how to compare two responses on a dimension (e.g.,
    correctness, conciseness, helpfulness). Every error during evaluation
    returns a neutral verdict rather than propagating an exception.
    """

    def __init__(self, name: str, weight: float = 1.0):
        """Initialize a scoring criterion.

        Args:
            name: Name of this criterion (e.g., "correctness", "conciseness")
            weight: Relative weight in the overall score (default 1.0)
        """
        self.name = name
        self.weight = max(0.0, weight)

    def score(self, a_response: str, b_response: str) -> tuple[float, float, str]:
        """Score both responses on this criterion.

        Args:
            a_response: Response from agent A
            b_response: Response from agent B

        Returns:
            (a_score, b_score, reason) where scores are 0-100 and reason explains
            the judgment. On error, returns (50, 50, error message).
        """
        try:
            return self._evaluate(a_response, b_response)
        except Exception as exc:
            return 50.0, 50.0, f"error during {self.name}: {exc}"

    def _evaluate(self, a_response: str, b_response: str) -> tuple[float, float, str]:
        """Subclasses override to implement the actual scoring logic."""
        raise NotImplementedError


class Judge:
    """Orchestrates the comparison of two agent responses.

    A Judge applies scoring criteria to determine which agent performed better.
    It aggregates per-criterion scores into a final verdict and always returns
    a complete Verdict, never raising.
    """

    def __init__(self, criteria: list[Criteria] | None = None):
        """Initialize a judge.

        Args:
            criteria: List of Criteria to apply. If None, uses default criteria.
        """
        self.criteria = criteria if criteria is not None else self._default_criteria()

    @staticmethod
    def _default_criteria() -> list[Criteria]:
        """Return default scoring criteria for when none are specified."""
        # Default: just check that both responses are non-empty
        return [LengthCriterion()]

    def judge(
        self,
        a_response: str,
        b_response: str,
        question: str = ""
    ) -> Verdict:
        """Compare two agent responses and return a verdict.

        Args:
            a_response: Output from agent A
            b_response: Output from agent B
            question: Optional context/question that prompted the responses

        Returns:
            A Verdict with scores and explanation. Every path returns a Verdict
            (never raises).
        """
        try:
            return self._evaluate(a_response, b_response, question)
        except Exception as exc:
            return Verdict(
                winner="tie",
                a_score=50.0,
                b_score=50.0,
                reason="",
                error=f"judge error: {exc}"
            )

    def _evaluate(
        self,
        a_response: str,
        b_response: str,
        question: str
    ) -> Verdict:
        """Perform the actual judgment."""
        if not self.criteria:
            return Verdict(
                winner="tie",
                a_score=50.0,
                b_score=50.0,
                reason="no scoring criteria defined",
            )

        total_a = 0.0
        total_b = 0.0
        total_weight = 0.0
        reasons = []

        # Score each criterion and accumulate weighted scores
        for criterion in self.criteria:
            a_score, b_score, reason = criterion.score(a_response, b_response)
            weight = criterion.weight

            total_a += a_score * weight
            total_b += b_score * weight
            total_weight += weight
            reasons.append(f"{criterion.name}: {reason}")

        if total_weight == 0:
            # All criteria had zero weight
            return Verdict(
                winner="tie",
                a_score=50.0,
                b_score=50.0,
                reason="all criteria have zero weight",
            )

        # Normalize to 0-100 range
        a_final = total_a / total_weight
        b_final = total_b / total_weight

        # Determine winner
        if a_final > b_final + 0.5:  # Small tolerance to avoid floating-point ties
            winner = "a"
        elif b_final > a_final + 0.5:
            winner = "b"
        else:
            winner = "tie"

        reason = "; ".join(reasons)

        return Verdict(
            winner=winner,
            a_score=a_final,
            b_score=b_final,
            reason=reason,
        )


class LengthCriterion(Criteria):
    """Score based on response length (as a proxy for depth/completeness)."""

    def __init__(self):
        super().__init__("length", weight=1.0)

    def _evaluate(self, a_response: str, b_response: str) -> tuple[float, float, str]:
        """Score based on response length."""
        a_len = len(a_response)
        b_len = len(b_response)

        # Prefer responses that are non-empty; strongly prefer longer over empty
        if a_len == 0 and b_len == 0:
            return 50.0, 50.0, "both empty"
        if a_len == 0:
            return 20.0, 80.0, "A is empty"
        if b_len == 0:
            return 80.0, 20.0, "B is empty"

        # Both non-empty: score based on relative length
        max_len = max(a_len, b_len)
        a_score = (a_len / max_len) * 100
        b_score = (b_len / max_len) * 100

        if abs(a_len - b_len) < 10:
            reason = "similar length"
        elif a_len > b_len:
            reason = f"A is longer ({a_len} vs {b_len})"
        else:
            reason = f"B is longer ({b_len} vs {a_len})"

        return a_score, b_score, reason


class ContentLengthCriterion(Criteria):
    """Score based on content length, ignoring whitespace."""

    def __init__(self):
        super().__init__("content_length", weight=1.0)

    def _evaluate(self, a_response: str, b_response: str) -> tuple[float, float, str]:
        """Score based on non-whitespace content."""
        a_content = len(a_response.split())
        b_content = len(b_response.split())

        if a_content == 0 and b_content == 0:
            return 50.0, 50.0, "both empty"
        if a_content == 0:
            return 20.0, 80.0, "A has no content"
        if b_content == 0:
            return 80.0, 20.0, "B has no content"

        max_content = max(a_content, b_content)
        a_score = (a_content / max_content) * 100
        b_score = (b_content / max_content) * 100

        if abs(a_content - b_content) < 5:
            reason = "similar content"
        elif a_content > b_content:
            reason = f"A has more content ({a_content} vs {b_content} words)"
        else:
            reason = f"B has more content ({b_content} vs {a_content} words)"

        return a_score, b_score, reason
