from collections.abc import Sequence

import pytest

from src.application.category_matcher import CategoryCandidate, CategoryMatcher
from src.domain.text_embedding import Embedding, EmbeddingError

# Fake 2D "meanings": the x axis is "animal", the y axis is "sky".
FAKE_EMBEDDINGS: dict[str, Embedding] = {
    "gato": (1.0, 0.0),
    "estrela": (0.0, 1.0),
    "Gatos dormem muito": (0.9, 0.1),
    "Meio a meio": (1.0, 1.0),
    "lua": (0.0, -1.0),
}
CATEGORY_LABELS = {"cat": "gato", "star": "estrela"}
THREE_CATEGORY_LABELS = {"cat": "gato", "star": "estrela", "moon": "lua"}


class FakeEmbedder:
    """Answers from a fixed table and records every request."""

    def __init__(self) -> None:
        self.requests: list[list[str]] = []

    def embed(self, texts: Sequence[str]) -> list[Embedding]:
        self.requests.append(list(texts))
        return [FAKE_EMBEDDINGS[text] for text in texts]


class OfflineEmbedder:
    def embed(self, texts: Sequence[str]) -> list[Embedding]:
        raise EmbeddingError("connection refused")


class InMemoryEmbeddingCache:
    def __init__(self, stored: dict[str, Embedding] | None = None) -> None:
        self.stored: dict[str, Embedding] = dict(stored or {})
        self.save_count = 0

    def load(self) -> dict[str, Embedding]:
        return dict(self.stored)

    def save(self, embeddings: dict[str, Embedding]) -> None:
        self.stored = dict(embeddings)
        self.save_count += 1


@pytest.fixture
def embedder() -> FakeEmbedder:
    return FakeEmbedder()


@pytest.fixture
def cache() -> InMemoryEmbeddingCache:
    return InMemoryEmbeddingCache()


@pytest.fixture
def matcher(embedder: FakeEmbedder, cache: InMemoryEmbeddingCache) -> CategoryMatcher:
    return CategoryMatcher(embedder, CATEGORY_LABELS, cache)


def test_the_first_candidate_is_the_category_closest_in_meaning(matcher: CategoryMatcher) -> None:
    assert matcher.candidates("Gatos dormem muito", count=1)[0].category == "cat"


def test_saves_the_label_embeddings_in_the_cache(
    matcher: CategoryMatcher, cache: InMemoryEmbeddingCache
) -> None:
    matcher.candidates("Gatos dormem muito", count=2)

    assert cache.stored == {"estrela": (0.0, 1.0), "gato": (1.0, 0.0)}


def test_embeds_the_labels_only_once_per_run(
    matcher: CategoryMatcher, embedder: FakeEmbedder
) -> None:
    matcher.candidates("Gatos dormem muito", count=2)
    matcher.candidates("Meio a meio", count=2)

    assert embedder.requests == [["Gatos dormem muito"], ["estrela", "gato"], ["Meio a meio"]]


def test_does_not_embed_labels_already_in_the_cache(embedder: FakeEmbedder) -> None:
    cache = InMemoryEmbeddingCache({"gato": (1.0, 0.0), "estrela": (0.0, 1.0)})

    CategoryMatcher(embedder, CATEGORY_LABELS, cache).candidates("Gatos dormem muito", count=2)

    assert (embedder.requests, cache.save_count) == ([["Gatos dormem muito"]], 0)


def test_embeds_only_the_labels_missing_from_the_cache(embedder: FakeEmbedder) -> None:
    cache = InMemoryEmbeddingCache({"gato": (1.0, 0.0)})

    CategoryMatcher(embedder, CATEGORY_LABELS, cache).candidates("Gatos dormem muito", count=2)

    assert embedder.requests[1] == ["estrela"]


def test_lets_an_offline_model_error_through(cache: InMemoryEmbeddingCache) -> None:
    matcher = CategoryMatcher(OfflineEmbedder(), CATEGORY_LABELS, cache)

    with pytest.raises(EmbeddingError):
        matcher.candidates("Gatos dormem muito", count=2)


def test_needs_at_least_two_categories(
    embedder: FakeEmbedder, cache: InMemoryEmbeddingCache
) -> None:
    with pytest.raises(ValueError):
        CategoryMatcher(embedder, {"cat": "gato"}, cache)


@pytest.fixture
def matcher_of_three(embedder: FakeEmbedder, cache: InMemoryEmbeddingCache) -> CategoryMatcher:
    return CategoryMatcher(embedder, THREE_CATEGORY_LABELS, cache)


def test_lists_the_candidates_most_similar_first(matcher_of_three: CategoryMatcher) -> None:
    candidates = matcher_of_three.candidates("Gatos dormem muito", count=3)

    assert [candidate.category for candidate in candidates] == ["cat", "star", "moon"]


def test_returns_only_as_many_candidates_as_asked(matcher_of_three: CategoryMatcher) -> None:
    assert len(matcher_of_three.candidates("Gatos dormem muito", count=2)) == 2


def test_a_candidate_carries_its_label_and_similarity(matcher_of_three: CategoryMatcher) -> None:
    best = matcher_of_three.candidates("Gatos dormem muito", count=1)[0]

    assert best == CategoryCandidate(
        category="cat", label="gato", similarity=pytest.approx(0.9939, abs=1e-4)
    )


def test_asking_for_more_candidates_than_categories_returns_them_all(
    matcher_of_three: CategoryMatcher,
) -> None:
    assert len(matcher_of_three.candidates("Gatos dormem muito", count=10)) == 3


def test_rejects_asking_for_no_candidates(matcher_of_three: CategoryMatcher) -> None:
    with pytest.raises(ValueError):
        matcher_of_three.candidates("Gatos dormem muito", count=0)
