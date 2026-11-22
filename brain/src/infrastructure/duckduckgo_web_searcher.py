from ddgs import DDGS
from ddgs.exceptions import DDGSException

from src.domain.web_search import SearchResult, WebSearchError

DEFAULT_BACKEND = "duckduckgo"


class DuckDuckGoWebSearcher:
    def __init__(self, client: DDGS, backend: str = DEFAULT_BACKEND) -> None:
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
            raise WebSearchError(str(error)) from error
        return [
            SearchResult(
                title=str(raw_result.get("title", "")),
                url=str(raw_result.get("href", "")),
                snippet=str(raw_result.get("body", "")),
            )
            for raw_result in raw_results
        ]
