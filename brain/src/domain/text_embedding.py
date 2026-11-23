import math
from collections.abc import Sequence
from typing import Protocol

Embedding = tuple[float, ...]
"""A text turned into a vector: texts with similar meaning get vectors pointing the same way."""


class EmbeddingError(Exception):
    """Raised when texts cannot be turned into embeddings (model offline, bad answer...)."""


class TextEmbedder(Protocol):
    def embed(self, texts: Sequence[str]) -> list[Embedding]:
        """One embedding per text, in the same order."""
        ...


class EmbeddingCache(Protocol):
    """Keeps embeddings that never change (like category names), so they are computed once."""

    def load(self) -> dict[str, Embedding]: ...

    def save(self, embeddings: dict[str, Embedding]) -> None: ...


def cosine_similarity(first: Embedding, second: Embedding) -> float:
    """How much two vectors point the same way: 1 same direction, 0 unrelated, -1 opposite.

    cos = (a · b) / (|a| × |b|). A zero vector has no direction, so it is unrelated (0.0).
    """
    if len(first) != len(second):
        raise ValueError(f"cannot compare embeddings of sizes {len(first)} and {len(second)}")
    dot_product = sum(a * b for a, b in zip(first, second, strict=True))
    lengths = math.hypot(*first) * math.hypot(*second)
    if lengths == 0.0:
        return 0.0
    return dot_product / lengths
