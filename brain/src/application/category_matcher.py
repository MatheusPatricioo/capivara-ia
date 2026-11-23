import logging
from collections.abc import Mapping
from dataclasses import dataclass

from src.domain.text_embedding import (
    Embedding,
    EmbeddingCache,
    TextEmbedder,
    cosine_similarity,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CategoryCandidate:
    """One category found by the embeddings, with the label the comparison used."""

    category: str
    label: str
    similarity: float


@dataclass(frozen=True)
class CategoryMatch:
    category: str
    similarity: float
    """Cosine similarity between the text and the category: closer to 1 is more alike."""
    margin: float
    """How far ahead of the second closest category it is. Near 0 means the model was torn."""


class CategoryMatcher:
    """Finds the category whose meaning is closest to a text, using embeddings.

    Each category is compared through a label in the same language as the texts (the
    discoveries are in Portuguese, the Quick, Draw! names in English). The label
    embeddings never change, so they are computed once and kept in a cache.
    """

    def __init__(
        self,
        embedder: TextEmbedder,
        category_labels: Mapping[str, str],
        cache: EmbeddingCache,
    ) -> None:
        if len(category_labels) < 2:
            raise ValueError("matching needs at least two categories to compare")
        self._embedder = embedder
        self._category_labels = dict(category_labels)
        self._cache = cache
        self._label_embeddings: dict[str, Embedding] | None = None

    def candidates(self, text: str, count: int) -> tuple[CategoryCandidate, ...]:
        """The count categories closest to the text, most similar first (the "retrieve").

        Raises EmbeddingError when the embedding model cannot be reached.
        """
        if count < 1:
            raise ValueError("ask for at least one candidate")
        (text_embedding,) = self._embedder.embed([text])
        label_embeddings = self._embeddings_of_labels()
        ranked = sorted(
            (
                CategoryCandidate(
                    category=category,
                    label=label,
                    similarity=cosine_similarity(text_embedding, label_embeddings[label]),
                )
                for category, label in self._category_labels.items()
            ),
            key=lambda candidate: candidate.similarity,
            reverse=True,
        )
        return tuple(ranked[:count])

    def closest(self, text: str) -> CategoryMatch:
        """Raises EmbeddingError when the embedding model cannot be reached."""
        best, second = self.candidates(text, count=2)
        return CategoryMatch(
            category=best.category,
            similarity=best.similarity,
            margin=best.similarity - second.similarity,
        )

    def _embeddings_of_labels(self) -> dict[str, Embedding]:
        """Loaded once per run; only labels missing from the cache are sent to the model."""
        if self._label_embeddings is not None:
            return self._label_embeddings
        cached = self._cache.load()
        missing_labels = sorted(set(self._category_labels.values()) - set(cached))
        if missing_labels:
            logger.info("Computing embeddings for %d category labels", len(missing_labels))
            cached.update(zip(missing_labels, self._embedder.embed(missing_labels), strict=True))
            self._cache.save(cached)
        self._label_embeddings = cached
        return cached
