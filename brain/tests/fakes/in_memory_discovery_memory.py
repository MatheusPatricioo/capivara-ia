from collections.abc import Sequence

from src.domain.discovery import Discovery
from src.domain.discovery_memory import RememberedDiscovery, memory_text
from src.domain.text_embedding import Embedding, TextEmbedder, cosine_similarity


class InMemoryDiscoveryMemory:
    """DiscoveryMemory kept in a dict: the same rules as the database, without the database."""

    def __init__(self, embedder: TextEmbedder) -> None:
        self._embedder = embedder
        self._memories: dict[str, tuple[Discovery, Embedding]] = {}

    def remember(self, file_name: str, discovery: Discovery) -> None:
        [embedding] = self._embedder.embed([memory_text(discovery)])
        self._memories[file_name] = (discovery, embedding)

    def recall(self, text: str, limit: int) -> list[RememberedDiscovery]:
        if not self._memories:
            return []
        [query_embedding] = self._embedder.embed([text])
        remembered = [
            RememberedDiscovery(discovery, cosine_similarity(query_embedding, embedding))
            for discovery, embedding in self._memories.values()
        ]
        remembered.sort(key=lambda memory: memory.similarity, reverse=True)
        return remembered[:limit]


class WordCountEmbedder:
    """Fake embedder: counts how often each vocabulary word appears in the text.

    Texts sharing words get vectors pointing the same way, which is enough to test
    "closest in meaning" without calling a real embedding model.
    """

    def __init__(self, vocabulary: Sequence[str]) -> None:
        self._vocabulary = tuple(word.lower() for word in vocabulary)

    def embed(self, texts: Sequence[str]) -> list[Embedding]:
        return [self._count_words(text) for text in texts]

    def _count_words(self, text: str) -> Embedding:
        words = text.lower().split()
        return tuple(float(words.count(word)) for word in self._vocabulary)


class ZeroPaddedEmbedder:
    """Fills another fake's embeddings with zeros up to `dimensions` numbers.

    The database only stores vectors of one size (768). Trailing zeros change neither
    the dot product nor the lengths, so the cosine similarity stays the same.
    """

    def __init__(self, embedder: TextEmbedder, dimensions: int) -> None:
        self._embedder = embedder
        self._dimensions = dimensions

    def embed(self, texts: Sequence[str]) -> list[Embedding]:
        return [self._pad(embedding) for embedding in self._embedder.embed(texts)]

    def _pad(self, embedding: Embedding) -> Embedding:
        return embedding + (0.0,) * (self._dimensions - len(embedding))
