from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str


class WebSearchError(Exception):
    """Raised when the web search cannot be completed (network failure, rate limit...)."""


class WebSearcher(Protocol):
    def search(self, query: str, max_results: int) -> list[SearchResult]: ...
