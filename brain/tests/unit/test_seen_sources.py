import pytest

from src.application.tools.seen_sources import SeenSources

SEARCHED_URL = "https://example.com/swim"
UNSEEN_URL = "https://example.com/made-up"


@pytest.fixture
def seen_sources() -> SeenSources:
    sources = SeenSources()
    sources.remember([SEARCHED_URL])
    return sources


def test_starts_empty() -> None:
    assert SeenSources().is_empty


def test_is_not_empty_after_remembering_a_url(seen_sources: SeenSources) -> None:
    assert not seen_sources.is_empty


def test_contains_a_remembered_url(seen_sources: SeenSources) -> None:
    assert seen_sources.contains(SEARCHED_URL)


def test_ignores_surrounding_spaces_when_checking(seen_sources: SeenSources) -> None:
    assert seen_sources.contains(f"  {SEARCHED_URL}  ")


def test_does_not_contain_a_url_it_never_saw(seen_sources: SeenSources) -> None:
    assert not seen_sources.contains(UNSEEN_URL)


def test_matches_a_link_written_with_encoded_accents() -> None:
    sources = SeenSources()
    sources.remember(["https://pt.wikipedia.org/wiki/Satélites_artificiais"])

    assert sources.contains("https://pt.wikipedia.org/wiki/Sat%C3%A9lites_artificiais")


def test_keeps_the_results_of_the_latest_search(seen_sources: SeenSources) -> None:
    seen_sources.remember(["https://example.com/a", "https://example.com/b"])

    assert seen_sources.latest_results == ("https://example.com/a", "https://example.com/b")


def test_a_search_without_results_keeps_the_previous_ones(seen_sources: SeenSources) -> None:
    seen_sources.remember([])

    assert seen_sources.latest_results == (SEARCHED_URL,)
