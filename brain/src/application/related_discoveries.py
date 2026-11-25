import logging
from collections.abc import Sequence
from typing import Protocol

from src.domain.discovery import Discovery
from src.domain.discovery_memory import DiscoveryMemory, DiscoveryMemoryError, RememberedDiscovery
from src.domain.language_model import LanguageModelError

DEFAULT_CANDIDATE_COUNT = 5

logger = logging.getLogger(__name__)


class QueryRewriter(Protocol):
    def expand(self, subject: str) -> str:
        """The text to search for this subject. Raises LanguageModelError."""
        ...


class MemoryChooser(Protocol):
    def choose(self, subject: str, candidates: Sequence[RememberedDiscovery]) -> Discovery | None:
        """The candidate really about the subject, or None. Raises LanguageModelError."""
        ...


class RelatedDiscoveries:
    """For each subject (something she noticed), the saved discovery really about it, if any.

    The pipeline has up to three steps:
    1. Query rewriting (optional, expander): "luzinhas piscando" also searches "vaga-lumes".
    2. Retrieve: the memory brings the closest discoveries; those below min_similarity are
       not even considered.
    3. Decide: with a chooser (rerank), the language model picks the one really about the
       subject, or none. Without it, the closest one counts when it reaches min_similarity.

    The evals (python -m src.run_evals --suite retrieval) measure each combination.
    """

    def __init__(
        self,
        memory: DiscoveryMemory,
        min_similarity: float,
        chooser: MemoryChooser | None = None,
        expander: QueryRewriter | None = None,
        candidate_count: int = DEFAULT_CANDIDATE_COUNT,
    ) -> None:
        self._memory = memory
        self._min_similarity = min_similarity
        self._chooser = chooser
        self._expander = expander
        self._candidate_count = candidate_count

    def about(self, subjects: Sequence[str]) -> list[Discovery]:
        """Related discoveries without repeats, in the order of the subjects.

        A memory failure returns nothing (logged) and stops at the first subject, so an
        offline database delays the cycle by one timeout, not one per subject.
        """
        try:
            related_per_subject = [self.closest_to(subject) for subject in subjects]
        except DiscoveryMemoryError as error:
            logger.warning("Could not recall related discoveries: %s", error)
            return []
        related: list[Discovery] = []
        for discovery in related_per_subject:
            if discovery is not None and discovery not in related:
                related.append(discovery)
        return related

    def closest_to(self, subject: str) -> Discovery | None:
        """The discovery about this subject, or None. Raises DiscoveryMemoryError."""
        query = self._query_for(subject)
        if self._chooser is None:
            return self._closest_above_threshold(subject, query)
        candidates = [
            candidate
            for candidate in self._memory.recall(query, limit=self._candidate_count)
            if candidate.similarity >= self._min_similarity
        ]
        try:
            return self._chooser.choose(subject, candidates)
        except LanguageModelError as error:
            logger.warning("Could not rerank the memories about '%s': %s", subject, error)
            return None

    def _query_for(self, subject: str) -> str:
        """A failed rewrite falls back to the subject itself: the search still works."""
        if self._expander is None:
            return subject
        try:
            return self._expander.expand(subject)
        except LanguageModelError as error:
            logger.warning("Could not rewrite the memory query for '%s': %s", subject, error)
            return subject

    def _closest_above_threshold(self, subject: str, query: str) -> Discovery | None:
        remembered = self._memory.recall(query, limit=1)
        if not remembered:
            return None
        [closest] = remembered
        self._log_closest(subject, closest)
        return closest.discovery if closest.similarity >= self._min_similarity else None

    def _log_closest(self, subject: str, closest: RememberedDiscovery) -> None:
        # Logged either way, so the threshold can be recalibrated from real cycles.
        is_related = closest.similarity >= self._min_similarity
        logger.info(
            "Closest memory to '%s': '%s' (%.3f, %s)",
            subject,
            closest.discovery.title,
            closest.similarity,
            "related" if is_related else "below the threshold",
        )
