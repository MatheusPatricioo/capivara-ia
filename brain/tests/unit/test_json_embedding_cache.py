from pathlib import Path

import pytest

from src.infrastructure.json_embedding_cache import JsonEmbeddingCache
from src.infrastructure.quickdraw_doodles import load_category_labels, load_doodle_library


@pytest.fixture
def cache_file(tmp_path: Path) -> Path:
    return tmp_path / "embeddings.cache.json"


def test_loads_nothing_before_the_first_save(cache_file: Path) -> None:
    assert JsonEmbeddingCache(cache_file, "nomic-embed-text").load() == {}


def test_loads_what_was_saved(cache_file: Path) -> None:
    cache = JsonEmbeddingCache(cache_file, "nomic-embed-text")
    cache.save({"gato": (0.5, -0.25)})

    assert cache.load() == {"gato": (0.5, -0.25)}


def test_ignores_embeddings_made_by_another_model(cache_file: Path) -> None:
    JsonEmbeddingCache(cache_file, "old-model").save({"gato": (0.5, -0.25)})

    assert JsonEmbeddingCache(cache_file, "nomic-embed-text").load() == {}


def test_ignores_an_unreadable_cache_file(cache_file: Path) -> None:
    cache_file.write_text("not json", encoding="utf-8")

    assert JsonEmbeddingCache(cache_file, "nomic-embed-text").load() == {}


def test_every_doodle_category_has_a_portuguese_label() -> None:
    """Without a label a category could never be matched to a discovery."""
    labels = load_category_labels()

    assert set(labels) == set(load_doodle_library().categories)
