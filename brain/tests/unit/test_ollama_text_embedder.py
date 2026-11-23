import json

import httpx
import pytest

from src.domain.text_embedding import EmbeddingError
from src.infrastructure.ollama_text_embedder import MAX_TEXTS_PER_REQUEST, OllamaTextEmbedder


class RecordingTransport(httpx.BaseTransport):
    """Fake Ollama: answers /api/embed with one tiny vector per text and records requests."""

    def __init__(self) -> None:
        self.request_bodies: list[dict[str, object]] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        self.request_bodies.append(body)
        vectors = [[float(len(text)), 1.0] for text in body["input"]]
        return httpx.Response(200, json={"model": body["model"], "embeddings": vectors})


@pytest.fixture
def transport() -> RecordingTransport:
    return RecordingTransport()


@pytest.fixture
def embedder(transport: RecordingTransport) -> OllamaTextEmbedder:
    client = httpx.Client(transport=transport, base_url="http://ollama")
    return OllamaTextEmbedder(client, "nomic-embed-text")


def answering(status_code: int, body: object) -> OllamaTextEmbedder:
    transport = httpx.MockTransport(lambda request: httpx.Response(status_code, json=body))
    return OllamaTextEmbedder(httpx.Client(transport=transport, base_url="http://ollama"), "m")


def test_returns_one_embedding_per_text_in_order(embedder: OllamaTextEmbedder) -> None:
    assert embedder.embed(["gato", "estrela"]) == [(4.0, 1.0), (7.0, 1.0)]


def test_sends_the_model_and_the_texts(
    embedder: OllamaTextEmbedder, transport: RecordingTransport
) -> None:
    embedder.embed(["gato"])

    assert transport.request_bodies == [{"model": "nomic-embed-text", "input": ["gato"]}]


def test_splits_long_lists_into_several_requests(
    embedder: OllamaTextEmbedder, transport: RecordingTransport
) -> None:
    embeddings = embedder.embed(["gato"] * (MAX_TEXTS_PER_REQUEST + 1))

    assert (len(embeddings), len(transport.request_bodies)) == (MAX_TEXTS_PER_REQUEST + 1, 2)


def test_sends_nothing_for_an_empty_list(
    embedder: OllamaTextEmbedder, transport: RecordingTransport
) -> None:
    assert (embedder.embed([]), transport.request_bodies) == ([], [])


def test_raises_an_embedding_error_when_ollama_fails() -> None:
    with pytest.raises(EmbeddingError, match="Could not get embeddings"):
        answering(500, {"error": "model not found"}).embed(["gato"])


def test_raises_an_embedding_error_on_an_unexpected_answer() -> None:
    with pytest.raises(EmbeddingError, match="Unexpected"):
        answering(200, {"vectors": []}).embed(["gato"])


def test_raises_when_ollama_returns_fewer_vectors_than_texts() -> None:
    with pytest.raises(EmbeddingError):
        answering(200, {"embeddings": [[1.0]]}).embed(["gato", "estrela"])
