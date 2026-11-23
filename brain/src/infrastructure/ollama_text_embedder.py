from collections.abc import Sequence

import httpx

from src.domain.text_embedding import Embedding, EmbeddingError

UNEXPECTED_FORMAT_MESSAGE = "Unexpected embedding response format from Ollama"
# Ollama refuses a request whose texts add up to more tokens than one batch holds
# (345 category names with a prefix already failed), so texts go in small groups.
MAX_TEXTS_PER_REQUEST = 32


class OllamaTextEmbedder:
    """Turns texts into embeddings with an Ollama embedding model (like nomic-embed-text).

    Uses POST /api/embed, which takes a list of texts and returns one vector per text;
    long lists (all the category names) are sent in groups of MAX_TEXTS_PER_REQUEST.
    """

    def __init__(self, client: httpx.Client, model: str) -> None:
        self._client = client
        self._model = model

    @property
    def model(self) -> str:
        return self._model

    def embed(self, texts: Sequence[str]) -> list[Embedding]:
        embeddings: list[Embedding] = []
        for start in range(0, len(texts), MAX_TEXTS_PER_REQUEST):
            embeddings.extend(self._embed_group(texts[start : start + MAX_TEXTS_PER_REQUEST]))
        return embeddings

    def _embed_group(self, texts: Sequence[str]) -> list[Embedding]:
        try:
            response = self._client.post(
                "/api/embed", json={"model": self._model, "input": list(texts)}
            )
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise EmbeddingError(f"Could not get embeddings from Ollama: {error}") from error
        return self._parse_embeddings(response, expected_count=len(texts))

    @staticmethod
    def _parse_embeddings(response: httpx.Response, expected_count: int) -> list[Embedding]:
        try:
            raw_embeddings = response.json()["embeddings"]
            embeddings = [tuple(float(value) for value in vector) for vector in raw_embeddings]
        except (ValueError, KeyError, TypeError) as error:
            raise EmbeddingError(UNEXPECTED_FORMAT_MESSAGE) from error
        if len(embeddings) != expected_count:
            raise EmbeddingError(UNEXPECTED_FORMAT_MESSAGE)
        return embeddings
