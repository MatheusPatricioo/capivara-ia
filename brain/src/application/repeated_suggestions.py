import logging
from dataclasses import dataclass

from src.domain.text_embedding import TextEmbedder, cosine_similarity
from src.domain.world_suggestion import WorldSuggestionArchive

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EarlierSuggestion:
    """A suggestion she already made, and how close in meaning it is to the new one."""

    request: str
    similarity: float


class RepeatedSuggestions:
    """Finds out whether a new request repeats one she already made, by meaning.

    "Vitórias-régias no lago" repeats "Um laguinho com vitórias-régias" even with other
    words. The limit is high on purpose: short requests about the same place (the pond,
    the garden) look alike to the embedding model even when the wish is different, and
    blocking a new wish is worse than letting a reworded one through (the developer reads
    every suggestion anyway). Calibrated with nomic-embed-text: different wishes reached
    0.727, wishes sharing their key words scored 0.80 to 0.90.
    """

    def __init__(
        self, archive: WorldSuggestionArchive, embedder: TextEmbedder, min_similarity: float
    ) -> None:
        self._archive = archive
        self._embedder = embedder
        self._min_similarity = min_similarity

    def earlier_version_of(self, request: str) -> EarlierSuggestion | None:
        """The closest earlier suggestion when it is close enough to count as the same wish.

        Raises EmbeddingError when the embedding model cannot be reached.
        """
        earlier_requests = [
            saved.suggestion.request for saved in self._archive.saved_suggestions()
        ]
        if not earlier_requests:
            return None
        request_embedding, *earlier_embeddings = self._embedder.embed(
            [request, *earlier_requests]
        )
        closest = max(
            (
                EarlierSuggestion(earlier, cosine_similarity(request_embedding, embedding))
                for earlier, embedding in zip(earlier_requests, earlier_embeddings, strict=True)
            ),
            key=lambda earlier_suggestion: earlier_suggestion.similarity,
        )
        logger.info(
            "Closest earlier suggestion to '%s': '%s' (%.3f)",
            request,
            closest.request,
            closest.similarity,
        )
        if closest.similarity < self._min_similarity:
            return None
        return closest
