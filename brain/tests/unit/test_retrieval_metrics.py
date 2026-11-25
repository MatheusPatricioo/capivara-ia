import pytest

from src.evals.retrieval_metrics import (
    DecisionOutcome,
    RetrievalOutcome,
    best_threshold,
    mean_reciprocal_rank,
    recall_at_k,
    summarize_decisions,
    threshold_decisions,
)

THRESHOLD = 0.70


def an_outcome(
    relevant_id: str | None, ranked_ids: tuple[str, ...], top_similarity: float = 0.9
) -> RetrievalOutcome:
    similarities = tuple(top_similarity - 0.01 * position for position in range(len(ranked_ids)))
    return RetrievalOutcome("pergunta", relevant_id, ranked_ids, similarities)


@pytest.fixture
def first_second_and_missing() -> list[RetrievalOutcome]:
    """Three answerable questions: right one 1st, right one 2nd, right one absent."""
    return [
        an_outcome("lua", ("lua", "sol")),
        an_outcome("sol", ("lua", "sol")),
        an_outcome("mar", ("lua", "sol")),
    ]


def test_recall_at_1_counts_only_right_answers_in_first_place(
    first_second_and_missing: list[RetrievalOutcome],
) -> None:
    assert recall_at_k(first_second_and_missing, 1) == pytest.approx(1 / 3)


def test_recall_at_2_also_counts_right_answers_in_second_place(
    first_second_and_missing: list[RetrievalOutcome],
) -> None:
    assert recall_at_k(first_second_and_missing, 2) == pytest.approx(2 / 3)


def test_mean_reciprocal_rank_averages_one_over_the_rank(
    first_second_and_missing: list[RetrievalOutcome],
) -> None:
    assert mean_reciprocal_rank(first_second_and_missing) == pytest.approx((1 + 0.5 + 0) / 3)


def test_unanswerable_questions_are_left_out_of_recall() -> None:
    outcomes = [an_outcome("lua", ("lua",)), an_outcome(None, ("sol",))]

    assert recall_at_k(outcomes, 1) == 1.0


def test_recall_is_zero_without_answerable_questions() -> None:
    assert recall_at_k([an_outcome(None, ("sol",))], 1) == 0.0


def test_right_answer_above_the_threshold_is_a_right_recall() -> None:
    decisions = threshold_decisions([an_outcome("lua", ("lua",), 0.80)], THRESHOLD)

    assert decisions.right_recall == 1


def test_wrong_answer_above_the_threshold_is_a_wrong_recall() -> None:
    decisions = threshold_decisions([an_outcome("lua", ("sol",), 0.80)], THRESHOLD)

    assert decisions.wrong_recall == 1


def test_unanswerable_question_above_the_threshold_is_a_wrong_recall() -> None:
    decisions = threshold_decisions([an_outcome(None, ("sol",), 0.80)], THRESHOLD)

    assert decisions.wrong_recall == 1


def test_answerable_question_below_the_threshold_is_missed() -> None:
    decisions = threshold_decisions([an_outcome("lua", ("lua",), 0.60)], THRESHOLD)

    assert decisions.missed == 1


def test_unanswerable_question_below_the_threshold_is_a_right_silence() -> None:
    decisions = threshold_decisions([an_outcome(None, ("sol",), 0.60)], THRESHOLD)

    assert decisions.right_silence == 1


def test_accuracy_counts_right_recalls_and_right_silences() -> None:
    outcomes = [
        an_outcome("lua", ("lua",), 0.80),
        an_outcome(None, ("sol",), 0.60),
        an_outcome("mar", ("sol",), 0.80),
        an_outcome("rio", ("rio",), 0.60),
    ]

    assert threshold_decisions(outcomes, THRESHOLD).accuracy == 0.5


def test_best_threshold_picks_the_one_with_most_right_decisions() -> None:
    outcomes = [an_outcome("lua", ("lua",), 0.80), an_outcome(None, ("sol",), 0.65)]

    threshold, summary = best_threshold(outcomes, [0.60, 0.70, 0.90])

    assert (threshold, summary.accuracy) == (0.70, 1.0)


def test_best_threshold_keeps_the_lowest_on_a_tie() -> None:
    outcomes = [an_outcome("lua", ("lua",), 0.80)]

    threshold, _ = best_threshold(outcomes, [0.75, 0.60])

    assert threshold == 0.60


def test_summarizes_decisions_from_any_rule() -> None:
    decisions = [
        DecisionOutcome("lua", "lua", "lua"),
        DecisionOutcome("sol", "sol", None),
        DecisionOutcome("mar", None, None),
    ]

    summary = summarize_decisions(decisions)

    assert (summary.right_recall, summary.missed, summary.right_silence) == (1, 1, 1)
