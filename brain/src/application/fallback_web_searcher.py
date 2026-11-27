"""When her usual search finds nothing, she tries a second place (Wikipedia) before giving up."""

import logging

from src.domain.web_search import SearchResult, WebSearcher, WebSearchError

logger = logging.getLogger(__name__)


class FallbackWebSearcher:
    """A decorator with the same interface as any WebSearcher.

    The primary searcher answers first. When it finds nothing, or fails (DuckDuckGo often
    blocks the network), the fallback searcher gets the same query. Whatever the fallback
    answers is final: if it also finds nothing, she found nothing.
    """

    def __init__(self, primary: WebSearcher, fallback: WebSearcher) -> None:
        self._primary = primary
        self._fallback = fallback

    def search(self, query: str, max_results: int) -> list[SearchResult]:
        try:
            main_results = self._primary.search(query, max_results)
        except WebSearchError as error:
            logger.warning("Main search failed (%s); trying the fallback", error)
            return self._fallback.search(query, max_results)
        if main_results:
            return main_results
        logger.info("Main search found nothing for %r; trying the fallback", query)
        return self._fallback.search(query, max_results)
