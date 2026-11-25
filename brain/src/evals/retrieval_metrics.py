"""Standard retrieval metrics, computed over a fixed set of questions with known answers."""

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievalOutcome:
    """What the memory returned for one question, compared with the right answer.

    relevant_id is the discovery that answers the question, or None when nothing in the
    memory does (then the right behaviour is to bring nothing back).
    ranked_ids and similarities come from the memory, the most similar first.
    """

    query: str
    relevant_id: str | None
    ranked_ids: tuple[str, ...]
    similarities: tuple[float, ...]

    @property
    def is_answerable(self) -> bool:
        return self.relevant_id is not None

    @property
    def rank(self) -> int | None:
        """1 when the right discovery came first, None when it did not come at all."""
        if self.relevant_id not in self.ranked_ids:
            return None
        return self.ranked_ids.index(self.relevant_id) + 1

    @property
    def top_similarity(self) -> float:
        return self.similarities[0] if self.similarities else 0.0


def recall_at_k(outcomes: Sequence[RetrievalOutcome], k: int) -> float:
    """Share of answerable questions whose right discovery is among the first k results."""
    answerable = _answerable(outcomes)
    if not answerable:
        return 0.0
    hits = sum(1 for outcome in answerable if outcome.rank is not None and outcome.rank <= k)
    return hits / len(answerable)


def mean_reciprocal_rank(outcomes: Sequence[RetrievalOutcome]) -> float:
    """Average of 1/rank: 1.0 when the right discovery always comes first, 0.5 when second..."""
    answerable = _answerable(outcomes)
    if not answerable:
        return 0.0
    return sum(_reciprocal_rank(outcome) for outcome in answerable) / len(answerable)


@dataclass(frozen=True)
class DecisionOutcome:
    """Which discovery, if any, went into her context for one question."""

    query: str
    relevant_id: str | None
    chosen_id: str | None


@dataclass(frozen=True)
class DecisionSummary:
    """How the final decisions split, for any decision rule (threshold or rerank):

    - right_recall: answerable, and the right discovery came back.
    - wrong_recall: something came back, but not the right discovery (noise in her context).
    - missed: answerable, but nothing came back.
    - right_silence: unanswerable, and nothing came back.
    """

    right_recall: int
    wrong_recall: int
    missed: int
    right_silence: int

    @property
    def total(self) -> int:
        return self.right_recall + self.wrong_recall + self.missed + self.right_silence

    @property
    def accuracy(self) -> float:
        if self.total == 0:
            return 0.0
        return (self.right_recall + self.right_silence) / self.total


def summarize_decisions(decisions: Sequence[DecisionOutcome]) -> DecisionSummary:
    right_recall = wrong_recall = missed = right_silence = 0
    for decision in decisions:
        if decision.chosen_id is None and decision.relevant_id is not None:
            missed += 1
        elif decision.chosen_id is None:
            right_silence += 1
        elif decision.chosen_id == decision.relevant_id:
            right_recall += 1
        else:
            wrong_recall += 1
    return DecisionSummary(right_recall, wrong_recall, missed, right_silence)


def decide_by_threshold(
    outcomes: Sequence[RetrievalOutcome], threshold: float
) -> list[DecisionOutcome]:
    """The first version of the rule: the closest discovery, only when it reaches threshold."""
    return [
        DecisionOutcome(
            outcome.query,
            outcome.relevant_id,
            outcome.ranked_ids[0] if outcome.top_similarity >= threshold else None,
        )
        for outcome in outcomes
    ]


def threshold_decisions(outcomes: Sequence[RetrievalOutcome], threshold: float) -> DecisionSummary:
    return summarize_decisions(decide_by_threshold(outcomes, threshold))


def best_threshold(
    outcomes: Sequence[RetrievalOutcome], thresholds: Sequence[float]
) -> tuple[float, DecisionSummary]:
    """The threshold with the most right decisions (the lowest one on a tie)."""
    summaries = [(value, threshold_decisions(outcomes, value)) for value in sorted(thresholds)]
    return max(summaries, key=lambda item: item[1].accuracy)


def _answerable(outcomes: Sequence[RetrievalOutcome]) -> list[RetrievalOutcome]:
    return [outcome for outcome in outcomes if outcome.is_answerable]


def _reciprocal_rank(outcome: RetrievalOutcome) -> float:
    rank = outcome.rank
    return 0.0 if rank is None else 1.0 / rank
