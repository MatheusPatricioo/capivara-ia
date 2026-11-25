from collections.abc import Sequence

from src.domain.text_embedding import Embedding
from src.infrastructure.task_prefixed_embedder import NOMIC_QUERY_PREFIX, TaskPrefixedEmbedder


class RecordingEmbedder:
    def __init__(self) -> None:
        self.received_texts: list[str] = []

    def embed(self, texts: Sequence[str]) -> list[Embedding]:
        self.received_texts.extend(texts)
        return [(1.0,) for _ in texts]


def test_puts_the_prefix_before_every_text() -> None:
    embedder = RecordingEmbedder()

    TaskPrefixedEmbedder(embedder, NOMIC_QUERY_PREFIX).embed(["lua", "sol"])

    assert embedder.received_texts == ["search_query: lua", "search_query: sol"]


def test_returns_one_embedding_per_text() -> None:
    embeddings = TaskPrefixedEmbedder(RecordingEmbedder(), NOMIC_QUERY_PREFIX).embed(["a", "b"])

    assert len(embeddings) == 2
