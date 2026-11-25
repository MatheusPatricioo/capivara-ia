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
class ThresholdDecisions:
    """How the "only the closest, and only above the threshold" rule decided each question.

    - right_recall: answerable, and the right discovery came back.
    - wrong_recall: something came back, but not the right discovery (noise in her context).
    - missed: answerable, but nothing came back (top similarity below the threshold).
    - right_silence: unanswerable, and nothing came back.
    """

    threshold: float
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


def threshold_decisions(
    outcomes: Sequence[RetrievalOutcome], threshold: float
) -> ThresholdDecisions:
    right_recall = wrong_recall = missed = right_silence = 0
    for outcome in outcomes:
        brought_back = outcome.top_similarity >= threshold
        if not brought_back and outcome.is_answerable:
            missed += 1
        elif not brought_back:
            right_silence += 1
        elif outcome.rank == 1:
            right_recall += 1
        else:
            wrong_recall += 1
    return ThresholdDecisions(threshold, right_recall, wrong_recall, missed, right_silence)


def _answerable(outcomes: Sequence[RetrievalOutcome]) -> list[RetrievalOutcome]:
    return [outcome for outcome in outcomes if outcome.is_answerable]


def _reciprocal_rank(outcome: RetrievalOutcome) -> float:
    rank = outcome.rank
    return 0.0 if rank is None else 1.0 / rank
