from typing import Any, Protocol

from ddgs.exceptions import DDGSException

from src.domain.web_search import SearchResult, WebSearchError

DEFAULT_BACKEND = "duckduckgo"
# ddgs raises a plain DDGSException with this exact message when the search
# worked but found nothing, instead of returning an empty list.
DDGS_NO_RESULTS_MESSAGE = "No results found."


class TextSearchClient(Protocol):
    """The part of the ddgs DDGS client this adapter uses."""

    def text(self, query: str, **kwargs: Any) -> list[dict[str, Any]]: ...


class DuckDuckGoWebSearcher:
    def __init__(self, client: TextSearchClient, backend: str = DEFAULT_BACKEND) -> None:
        self._client = client
        self._backend = backend

    def search(self, query: str, max_results: int) -> list[SearchResult]:
        try:
            raw_results = self._client.text(
                query,
                max_results=max_results,
                backend=self._backend,
            )
        except DDGSException as error:
            if str(error) == DDGS_NO_RESULTS_MESSAGE:
                return []
            raise WebSearchError(str(error)) from error
        return [
            SearchResult(
                title=str(raw_result.get("title", "")),
                url=str(raw_result.get("href", "")),
                snippet=str(raw_result.get("body", "")),
            )
            for raw_result in raw_results
        ]
