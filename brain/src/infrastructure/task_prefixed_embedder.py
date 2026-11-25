"""Task prefixes for embedding models trained with them, like nomic-embed-text.

nomic-embed-text was trained to see what a text is for: "search_document: " before what
is stored, "search_query: " before what is searched. Without the prefixes the model works,
but stored texts and short searches land further apart than they should.
"""

from collections.abc import Sequence

from src.domain.text_embedding import Embedding, TextEmbedder

NOMIC_DOCUMENT_PREFIX = "search_document: "
NOMIC_QUERY_PREFIX = "search_query: "


class TaskPrefixedEmbedder:
    """Decorator that puts the same prefix before every text sent to another embedder."""

    def __init__(self, embedder: TextEmbedder, prefix: str) -> None:
        self._embedder = embedder
        self._prefix = prefix

    def embed(self, texts: Sequence[str]) -> list[Embedding]:
        return self._embedder.embed([f"{self._prefix}{text}" for text in texts])
