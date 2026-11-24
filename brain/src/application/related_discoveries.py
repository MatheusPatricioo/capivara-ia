import logging
from collections.abc import Sequence

from src.domain.discovery import Discovery
from src.domain.discovery_memory import DiscoveryMemory, DiscoveryMemoryError, RememberedDiscovery

logger = logging.getLogger(__name__)


class RelatedDiscoveries:
    """For each subject (something she noticed), the saved discovery closest in meaning.

    Only the closest one per subject, and only when its similarity reaches min_similarity.
    Measured with nomic-embed-text on the world's noticed things: the closest discovery
    was the right one in 6 of 7 related pairs (all at 0.74 or more), while the second
    closest was often unrelated and still scored up to 0.75, so taking more than one per
    subject brings noise. Wrong "closest" discoveries scored below 0.67.
    """

    def __init__(self, memory: DiscoveryMemory, min_similarity: float) -> None:
        self._memory = memory
        self._min_similarity = min_similarity

    def about(self, subjects: Sequence[str]) -> list[Discovery]:
        """Related discoveries without repeats, in the order of the subjects.

        A memory failure returns nothing (logged) and stops at the first subject, so an
        offline database delays the cycle by one timeout, not one per subject.
        """
        try:
            closest = [self._closest(subject) for subject in subjects]
        except DiscoveryMemoryError as error:
            logger.warning("Could not recall related discoveries: %s", error)
            return []
        related: list[Discovery] = []
        for remembered in closest:
            if remembered is not None and remembered.discovery not in related:
                related.append(remembered.discovery)
        return related

    def _closest(self, subject: str) -> RememberedDiscovery | None:
        remembered = self._memory.recall(subject, limit=1)
        if not remembered:
            return None
        [closest] = remembered
        is_related = closest.similarity >= self._min_similarity
        # Logged either way, so the threshold can be recalibrated from real cycles.
        logger.info(
            "Closest memory to '%s': '%s' (%.3f, %s)",
            subject,
            closest.discovery.title,
            closest.similarity,
            "related" if is_related else "below the threshold",
        )
        return closest if is_related else None
