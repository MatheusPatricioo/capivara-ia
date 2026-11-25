import pytest

from src.application.fallback_web_searcher import FallbackWebSearcher
from src.domain.web_search import SearchResult, WebSearchError

QUERY = "insetos noturnos bioluminescentes"
MAX_RESULTS = 3
BLOG_RESULT = SearchResult("Insetos que brilham", "https://example.com/blog", "Vaga-lumes...")
WIKIPEDIA_RESULT = SearchResult(
    "Bioluminescência", "https://pt.wikipedia.org/wiki/Bioluminesc%C3%AAncia", "Produção de luz..."
)


class FixedSearcher:
    """Always answers the same results and records the queries it received."""

    def __init__(self, results: list[SearchResult]) -> None:
        self._results = results
        self.received_queries: list[tuple[str, int]] = []

    def search(self, query: str, max_results: int) -> list[SearchResult]:
        self.received_queries.append((query, max_results))
        return self._results


class FailingSearcher:
    def search(self, query: str, max_results: int) -> list[SearchResult]:
        raise WebSearchError("202 Ratelimit")


@pytest.fixture
def wikipedia() -> FixedSearcher:
    return FixedSearcher([WIKIPEDIA_RESULT])


def test_keeps_the_main_results_when_there_are_some(wikipedia: FixedSearcher) -> None:
    searcher = FallbackWebSearcher(FixedSearcher([BLOG_RESULT]), wikipedia)

    assert searcher.search(QUERY, MAX_RESULTS) == [BLOG_RESULT]


def test_does_not_ask_the_fallback_when_the_main_search_found_something(
    wikipedia: FixedSearcher,
) -> None:
    searcher = FallbackWebSearcher(FixedSearcher([BLOG_RESULT]), wikipedia)

    searcher.search(QUERY, MAX_RESULTS)

    assert wikipedia.received_queries == []


def test_asks_the_fallback_the_same_query_when_the_main_search_finds_nothing(
    wikipedia: FixedSearcher,
) -> None:
    searcher = FallbackWebSearcher(FixedSearcher([]), wikipedia)

    results = searcher.search(QUERY, MAX_RESULTS)

    assert (results, wikipedia.received_queries) == ([WIKIPEDIA_RESULT], [(QUERY, MAX_RESULTS)])


def test_asks_the_fallback_when_the_main_search_fails(wikipedia: FixedSearcher) -> None:
    searcher = FallbackWebSearcher(FailingSearcher(), wikipedia)

    assert searcher.search(QUERY, MAX_RESULTS) == [WIKIPEDIA_RESULT]


def test_finds_nothing_when_the_fallback_also_finds_nothing() -> None:
    searcher = FallbackWebSearcher(FixedSearcher([]), FixedSearcher([]))

    assert searcher.search(QUERY, MAX_RESULTS) == []


def test_raises_when_both_searches_fail() -> None:
    searcher = FallbackWebSearcher(FailingSearcher(), FailingSearcher())

    with pytest.raises(WebSearchError):
        searcher.search(QUERY, MAX_RESULTS)
