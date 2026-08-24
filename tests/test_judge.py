"""Tests for awrena judging logic.

Every path must return a valid Verdict. This suite tests:
- Happy path: both agents respond, verdict is computed
- Error paths: empty responses, malformed input, exceptions
- Criteria scoring: length-based, content-based
"""


from awrena import ContentLengthCriterion, Criteria, Judge, LengthCriterion, Verdict


class TestVerdictBasics:
    """Test the Verdict dataclass itself."""

    def test_verdict_is_valid_when_no_error(self):
        """A verdict with no error is valid."""
        v = Verdict(winner="a", a_score=75.0, b_score=25.0, reason="A is better")
        assert v.is_valid()
        assert v.error is None

    def test_verdict_is_invalid_with_error(self):
        """A verdict with an error message is invalid."""
        v = Verdict(
            winner="tie",
            a_score=50.0,
            b_score=50.0,
            reason="",
            error="could not judge"
        )
        assert not v.is_valid()
        assert v.error is not None

    def test_verdict_summary_shows_error(self):
        """Summary displays the error when present."""
        v = Verdict(
            winner="tie",
            a_score=50.0,
            b_score=50.0,
            reason="",
            error="judge failed"
        )
        summary = v.summary()
        assert "UNSCORED" in summary
        assert "judge failed" in summary

    def test_verdict_summary_shows_result(self):
        """Summary displays the winner and scores."""
        v = Verdict(winner="a", a_score=80.0, b_score=20.0, reason="A won")
        summary = v.summary()
        assert "A wins" in summary or "a wins" in summary
        assert "80" in summary
        assert "20" in summary


class TestLengthCriterion:
    """Test scoring based on response length."""

    def test_both_empty_is_tie(self):
        """Empty responses should score equally."""
        criterion = LengthCriterion()
        a_score, b_score, reason = criterion.score("", "")
        assert a_score == b_score == 50.0
        assert "empty" in reason.lower()

    def test_one_empty_strongly_penalized(self):
        """One empty response should lose badly."""
        criterion = LengthCriterion()
        a_score, b_score, reason = criterion.score("", "response")
        assert a_score < 50.0
        assert b_score > 50.0
        assert "empty" in reason.lower()

    def test_longer_response_wins(self):
        """Longer response should score higher."""
        criterion = LengthCriterion()
        a_score, b_score, reason = criterion.score("short", "much longer response")
        assert b_score > a_score
        assert "longer" in reason.lower()

    def test_similar_length_scores_similarly(self):
        """Responses of similar length should score close."""
        criterion = LengthCriterion()
        a_score, b_score, reason = criterion.score("abcde", "fghij")
        assert abs(a_score - b_score) < 10
        assert "similar" in reason.lower()

    def test_exact_same_length_ties(self):
        """Identical length should tie."""
        criterion = LengthCriterion()
        a_score, b_score, reason = criterion.score("hello", "world")
        assert a_score == b_score


class TestContentLengthCriterion:
    """Test scoring based on word count."""

    def test_both_empty_is_tie(self):
        """Empty content should score equally."""
        criterion = ContentLengthCriterion()
        a_score, b_score, reason = criterion.score("", "")
        assert a_score == b_score == 50.0

    def test_word_count_matters(self):
        """More words should score higher."""
        criterion = ContentLengthCriterion()
        a_score, b_score, reason = criterion.score("one", "one two three four five six seven eight")
        assert b_score > a_score
        assert "more content" in reason.lower() or "words" in reason.lower()

    def test_whitespace_ignored(self):
        """Extra whitespace shouldn't affect scoring."""
        criterion = ContentLengthCriterion()
        a_score_1, b_score_1, _ = criterion.score("hello world", "hello world")
        a_score_2, b_score_2, _ = criterion.score(
            "hello   world",
            "hello\n\nworld"
        )
        assert a_score_1 == a_score_2
        assert b_score_1 == b_score_2


class TestJudge:
    """Test the Judge orchestrator."""

    def test_judge_with_default_criteria(self):
        """Judge uses default criteria when none provided."""
        judge = Judge()
        verdict = judge.judge("response A", "response B")
        assert verdict.is_valid()
        assert verdict.winner in ["a", "b", "tie"]

    def test_judge_never_raises(self):
        """Judge always returns a Verdict, never raises."""
        judge = Judge([LengthCriterion()])
        # Try pathological inputs
        verdict = judge.judge("", "")
        assert isinstance(verdict, Verdict)

        verdict = judge.judge("a" * 1000000, "b" * 1000000)
        assert isinstance(verdict, Verdict)

    def test_judge_returns_valid_verdict(self):
        """Successful judgment returns valid verdict."""
        judge = Judge([LengthCriterion()])
        verdict = judge.judge("short", "much longer response", "question?")
        assert verdict.is_valid()
        assert verdict.error is None
        assert verdict.winner in ["a", "b", "tie"]
        assert verdict.a_score >= 0 and verdict.a_score <= 100
        assert verdict.b_score >= 0 and verdict.b_score <= 100

    def test_judge_longer_response_wins(self):
        """Longer response should be judged better."""
        judge = Judge([LengthCriterion()])
        verdict = judge.judge("x", "x" * 100)
        assert verdict.is_valid()
        assert verdict.winner == "b", "Longer response should win"
        assert verdict.b_score > verdict.a_score

    def test_judge_with_multiple_criteria(self):
        """Judge aggregates scores from multiple criteria."""
        criteria = [LengthCriterion(), ContentLengthCriterion()]
        judge = Judge(criteria)
        verdict = judge.judge("short", "much longer response here")
        assert verdict.is_valid()
        # Both criteria favor B
        assert verdict.winner == "b"

    def test_judge_with_empty_criteria_list(self):
        """Judge handles empty criteria list gracefully."""
        judge = Judge([])
        verdict = judge.judge("A", "B")
        # Empty criteria returns a tie verdict with explanation
        assert verdict.winner == "tie"

    def test_judge_scores_are_normalized(self):
        """Judge scores are normalized to 0-100 range."""
        judge = Judge([LengthCriterion()])
        verdict = judge.judge("a", "b")
        assert 0 <= verdict.a_score <= 100
        assert 0 <= verdict.b_score <= 100

    def test_identical_responses_tie(self):
        """Identical responses should tie."""
        judge = Judge([LengthCriterion(), ContentLengthCriterion()])
        verdict = judge.judge("same response", "same response")
        assert verdict.winner == "tie"

    def test_empty_vs_nonempty_favors_nonempty(self):
        """Empty response loses to any non-empty response."""
        judge = Judge([LengthCriterion()])
        verdict = judge.judge("", "anything")
        assert verdict.winner == "b"
        assert verdict.b_score > verdict.a_score


class TestCriteriaErrorHandling:
    """Test that criteria handle errors gracefully."""

    def test_criterion_score_never_raises(self):
        """Criterion.score() must never raise, always returns (a, b, reason)."""
        # Create a criterion that would normally fail
        criterion = LengthCriterion()
        a_score, b_score, reason = criterion.score("test", "test")
        # Even with pathological inputs, it returns scores
        assert isinstance(a_score, (int, float))
        assert isinstance(b_score, (int, float))
        assert isinstance(reason, str)

    def test_bad_criterion_returns_neutral_scores(self):
        """A criterion that raises returns neutral (50, 50, error_msg)."""
        class BrokenCriterion(Criteria):
            def _evaluate(self, a, b):
                raise RuntimeError("broken")

        broken = BrokenCriterion("broken")
        a_score, b_score, reason = broken.score("a", "b")
        assert a_score == 50.0
        assert b_score == 50.0
        assert "error" in reason.lower()

    def test_broken_criterion_doesnt_break_judge(self):
        """Judge handles broken criteria without raising."""
        class BrokenCriterion(Criteria):
            def _evaluate(self, a, b):
                raise RuntimeError("broken")

        judge = Judge([BrokenCriterion("broken")])
        verdict = judge.judge("a", "b")
        # Judge should still return a valid verdict
        assert verdict.is_valid()
        # The reason should mention the broken criterion
        assert "broken" in verdict.reason.lower()


class TestWinnerDetermination:
    """Test logic for determining the winner."""

    def test_clear_winner_a(self):
        """Clear difference should crown a winner."""
        judge = Judge([LengthCriterion()])
        verdict = judge.judge("x" * 100, "x")
        assert verdict.winner == "a"
        assert verdict.a_score > verdict.b_score

    def test_clear_winner_b(self):
        """Clear difference should crown a winner."""
        judge = Judge([LengthCriterion()])
        verdict = judge.judge("x", "x" * 100)
        assert verdict.winner == "b"
        assert verdict.b_score > verdict.a_score

    def test_very_close_scores_tie(self):
        """Very similar scores should result in a tie."""
        judge = Judge([ContentLengthCriterion()])
        # Two responses with exactly the same word count
        verdict = judge.judge("one two three", "four five six")
        assert verdict.winner == "tie"

    def test_small_difference_ties_or_wins(self):
        """Small differences are handled consistently."""
        judge = Judge([LengthCriterion()])
        verdict = judge.judge("hello world", "hello world ")
        # Slight length difference; judge should still have a winner or tie
        assert verdict.winner in ["a", "b", "tie"]


class TestJudgeIntegration:
    """Integration tests for the full judging pipeline."""

    def test_full_judgment_pipeline(self):
        """Full end-to-end judgment works correctly."""
        judge = Judge([LengthCriterion(), ContentLengthCriterion()])

        verdict = judge.judge(
            a_response="Agent A produced this short response.",
            b_response=(
                "Agent B produced a much longer and more detailed response with "
                "additional information and explanation."
            ),
            question="What is your answer?"
        )

        # Should have a valid, complete verdict
        assert verdict.is_valid()
        assert verdict.winner in ["a", "b", "tie"]
        assert verdict.reason != ""
        # B is longer, should win
        assert verdict.winner == "b"
        assert verdict.b_score > verdict.a_score

    def test_question_parameter_accepted(self):
        """Judge accepts optional question parameter."""
        judge = Judge([LengthCriterion()])
        verdict = judge.judge(
            a_response="answer",
            b_response="answer",
            question="What is 2+2?"
        )
        assert verdict.is_valid()

    def test_verdict_reason_is_informative(self):
        """Verdict reason should explain the judgment."""
        judge = Judge([LengthCriterion()])
        verdict = judge.judge("short", "much longer response here")
        assert verdict.reason != ""
        # Should mention the criterion
        assert "length" in verdict.reason.lower()
