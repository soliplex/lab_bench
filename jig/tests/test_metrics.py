"""What the ported metric definitions must do.

These pin semantics rather than exercise code. The kernel is a dozen
lines, and every one of them decides how a recorded rate reads: whether
an unlabelled question scores zero or nothing, whether a gold document
that was never retrieved still counts against the score, whether a
window of k can be beaten by a gold set larger than k. A defect in any
of those completes a run and prints a plausible table.
"""

from __future__ import annotations

import pytest

from retrieval_failures import metrics


class TestAveragePrecision:
    def test_a_perfect_ranking_scores_one(self):
        ranked = ["a", "b", "x"]

        result = metrics.average_precision(ranked, {"a", "b"})

        assert result == 1.0

    def test_unretrieved_gold_still_counts_in_the_denominator(self):
        ranked = ["a", "x", "y"]

        result = metrics.average_precision(ranked, {"a", "b"})

        assert result == 0.5

    def test_a_non_relevant_hit_lowers_later_precision(self):
        ranked = ["a", "x", "b"]

        result = metrics.average_precision(ranked, {"a", "b"})

        assert result == pytest.approx((1.0 + 2 / 3) / 2)

    def test_nothing_relevant_retrieved_scores_zero(self):
        ranked = ["x", "y"]

        result = metrics.average_precision(ranked, {"a"})

        assert result == 0.0

    @pytest.mark.parametrize(
        ("ranked", "expected"),
        [
            (["a", "x", "y"], 1.0),
            (["x", "a", "y"], 0.5),
            (["x", "y", "a"], 1 / 3),
        ],
    )
    def test_a_singleton_gold_set_is_reciprocal_rank(self, ranked, expected):
        result = metrics.average_precision(ranked, {"a"})

        assert result == pytest.approx(expected)

    @pytest.mark.parametrize("gold", [set(), [], None])
    def test_an_unlabelled_case_is_ineligible_not_zero(self, gold):
        result = metrics.average_precision(["a"], gold or ())

        assert result is None


class TestRecallAt:
    def test_counts_gold_inside_the_window(self):
        ranked = ["a", "x", "b"]

        result = metrics.recall_at(ranked, {"a", "b"}, 2)

        assert result == 0.5

    def test_is_not_capped_at_k(self):
        # Three gold documents cannot all appear in a window of two, and
        # the score says so rather than flattering the ranking.
        ranked = ["a", "b", "c"]

        result = metrics.recall_at(ranked, {"a", "b", "c"}, 2)

        assert result == pytest.approx(2 / 3)

    def test_an_unlabelled_case_is_ineligible(self):
        result = metrics.recall_at(["a"], set(), 5)

        assert result is None


class TestNdcgAt:
    def test_a_perfect_ordering_scores_one(self):
        ranked = ["a", "b", "x"]

        result = metrics.ndcg_at(ranked, {"a", "b"}, 2)

        assert result == pytest.approx(1.0)

    def test_the_ideal_is_capped_at_k(self):
        # Unlike recall: a full window is the best a window can do, even
        # with more gold outside it.
        ranked = ["a", "b"]

        result = metrics.ndcg_at(ranked, {"a", "b", "c"}, 2)

        assert result == pytest.approx(1.0)

    def test_a_lower_rank_scores_less(self):
        ranked = ["x", "a"]

        result = metrics.ndcg_at(ranked, {"a"}, 2)

        assert result == pytest.approx(1 / 1.584962500721156)

    def test_an_unlabelled_case_is_ineligible(self):
        result = metrics.ndcg_at(["a"], set(), 5)

        assert result is None


class TestRankOf:
    def test_reports_a_one_based_rank(self):
        ranked = ["x", "a", "y"]

        result = metrics.rank_of(ranked, "a")

        assert result == 2

    def test_an_absent_identifier_has_no_rank(self):
        result = metrics.rank_of(["x", "y"], "a")

        assert result is None


class TestShareOf:
    def test_counts_repeats_within_the_window(self):
        ranked = ["a", "b", "a", "a"]

        result = metrics.share_of(ranked, "a")

        assert result == 0.75

    def test_an_empty_window_has_no_share(self):
        result = metrics.share_of([], "a")

        assert result is None


class TestDeduplicate:
    def test_keeps_the_first_occurrence_in_order(self):
        ranked = ["b", "a", "b", "c", "a"]

        result = metrics.deduplicate(ranked)

        assert result == ["b", "a", "c"]


class TestMean:
    def test_ineligible_values_leave_the_denominator(self):
        values = [1.0, None, 0.0]

        result = metrics.mean(values)

        assert result == 0.5

    def test_all_ineligible_means_no_score(self):
        result = metrics.mean([None, None])

        assert result is None

    def test_no_values_at_all_means_no_score(self):
        result = metrics.mean([])

        assert result is None


class TestRender:
    def test_an_ineligible_value_renders_as_a_dash(self):
        result = metrics.render(None)

        assert result == "--"

    def test_zero_renders_as_a_number(self):
        # The distinction the dash exists to preserve.
        result = metrics.render(0.0)

        assert result == "0.000"
