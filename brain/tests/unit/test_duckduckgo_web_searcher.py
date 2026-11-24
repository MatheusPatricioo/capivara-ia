from typing import Any

import pytest
from ddgs.exceptions import DDGSException

from src.domain.web_search import SearchResult, WebSearchError
from src.infrastructure.duckduckgo_web_searcher import DuckDuckGoWebSearcher

QUERY = "capybara diet"
MAX_RESULTS = 3
RAW_GRASS_RESULT = {
    "title": "What capybaras eat",
    "href": "https://example.com/diet",
    "body": "Mostly grass.",
}


class FakeDDGS:
    """Returns canned raw results and records the arguments of each search."""

    def __init__(self, raw_results: list[dict[str, Any]]) -> None:
        self._raw_results = raw_results
        self.received_calls: list[tuple[str, dict[str, Any]]] = []

    def text(self, query: str, **kwargs: Any) -> list[dict[str, Any]]:
        self.received_calls.append((query, kwargs))
        return self._raw_results


class FailingDDGS:
    """Raises a DDGSException with the given message, like ddgs does."""

    def __init__(self, message: str) -> None:
        self._message = message

    def text(self, query: str, **kwargs: Any) -> list[dict[str, Any]]:
        raise DDGSException(self._message)


@pytest.fixture
def fake_ddgs() -> FakeDDGS:
    return FakeDDGS([RAW_GRASS_RESULT])


def test_converts_raw_results_into_search_results(fake_ddgs: FakeDDGS) -> None:
    searcher = DuckDuckGoWebSearcher(fake_ddgs)

    results = searcher.search(QUERY, MAX_RESULTS)

    assert results == [
        SearchResult(
            title="What capybaras eat",
            url="https://example.com/diet",
            snippet="Mostly grass.",
        )
    ]


def test_passes_the_result_limit_backend_and_region_to_ddgs(fake_ddgs: FakeDDGS) -> None:
    searcher = DuckDuckGoWebSearcher(fake_ddgs, backend="auto", region="us-en")

    searcher.search(QUERY, MAX_RESULTS)

    assert fake_ddgs.received_calls == [
        (QUERY, {"max_results": MAX_RESULTS, "backend": "auto", "region": "us-en"})
    ]


def test_searches_brazilian_results_by_default(fake_ddgs: FakeDDGS) -> None:
    searcher = DuckDuckGoWebSearcher(fake_ddgs)

    searcher.search(QUERY, MAX_RESULTS)

    assert fake_ddgs.received_calls[0][1]["region"] == "br-pt"


def test_returns_an_empty_list_when_ddgs_finds_nothing() -> None:
    searcher = DuckDuckGoWebSearcher(FailingDDGS("No results found."))

    assert searcher.search(QUERY, MAX_RESULTS) == []


def test_turns_other_ddgs_errors_into_web_search_errors() -> None:
    searcher = DuckDuckGoWebSearcher(FailingDDGS("https://duckduckgo.com 202 Ratelimit"))

    with pytest.raises(WebSearchError, match="Ratelimit"):
        searcher.search(QUERY, MAX_RESULTS)


def test_keeps_only_the_first_of_several_glued_titles() -> None:
    second_title = "Lua: características, fases, origem, formação - Brasil Escola"
    glued_result = {
        "title": "Lua: características, fases, eclipse, origem e mais - Toda ..."
        f"{second_title}Lua: o que é, origem, características, superfície, atmosfera ...",
        "href": "https://www.todamateria.com.br/caracteristicas-da-lua/",
        "body": "A Lua é o único satélite natural da Terra.",
    }
    second_result = {"title": second_title, "href": "https://example.com/lua", "body": "Fases."}
    searcher = DuckDuckGoWebSearcher(FakeDDGS([glued_result, second_result]))

    results = searcher.search(QUERY, MAX_RESULTS)

    assert [result.title for result in results] == [
        "Lua: características, fases, eclipse, origem e mais - Toda ...",
        second_title,
    ]
