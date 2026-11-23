import logging
from collections.abc import Callable
from datetime import date, datetime

from src.application.tools.seen_sources import SeenSources
from src.domain.language_model import ToolDefinition
from src.domain.search_history import SearchHistory, SearchHistoryError
from src.domain.search_log import FoundPage, SearchLog, SearchLogError, SearchRecord
from src.domain.tool import ToolError
from src.domain.web_search import SearchResult, WebSearcher, WebSearchError

DEFAULT_MAX_RESULTS = 5
DEFAULT_MAX_SNIPPET_LENGTH = 300
# Says right away that an empty search leaves nothing to save, so the model does not
# try save_discovery without sources and burn the remaining steps on refusals.
NO_RESULTS_MESSAGE = (
    "No results found, so there is nothing from this search to save. Try other words, or move on."
)
ELLIPSIS = "..."
ALREADY_SEARCHED_MESSAGE = (
    "You already searched '{query}' on {searched_on}, so you know this already. "
    "Search for something different or a neighbouring subject, or move on."
)

logger = logging.getLogger(__name__)


def _local_now() -> datetime:
    return datetime.now().astimezone()


class WebSearchTool:
    def __init__(
        self,
        web_searcher: WebSearcher,
        max_results: int = DEFAULT_MAX_RESULTS,
        max_snippet_length: int = DEFAULT_MAX_SNIPPET_LENGTH,
        seen_sources: SeenSources | None = None,
        search_history: SearchHistory | None = None,
        today: Callable[[], date] = date.today,
        search_log: SearchLog | None = None,
        now: Callable[[], datetime] = _local_now,
    ) -> None:
        self._web_searcher = web_searcher
        self._max_results = max_results
        self._max_snippet_length = max_snippet_length
        self._seen_sources = seen_sources if seen_sources is not None else SeenSources()
        self._search_history = search_history
        self._today = today
        self._search_log = search_log
        self._now = now

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="web_search",
            description="Searches the web and returns a few results with title, URL and snippet.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What to search for, written in Brazilian Portuguese.",
                    },
                },
                "required": ["query"],
            },
        )

    def run(self, arguments: dict[str, object]) -> str:
        query = arguments.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ToolError("the 'query' argument must be a non-empty text")
        query = query.strip()
        searched_on = self._previous_search_day(query)
        if searched_on is not None:
            logger.info("web_search skipped: '%s' was already searched on %s", query, searched_on)
            return ALREADY_SEARCHED_MESSAGE.format(query=query, searched_on=searched_on.isoformat())
        try:
            results = self._web_searcher.search(query, self._max_results)
        except WebSearchError as error:
            raise ToolError(f"web search failed: {error}") from error
        limited_results = results[: self._max_results]
        self._seen_sources.remember(result.url for result in limited_results)
        logger.info("web_search returned %d result(s)", len(limited_results))
        self._log_search(query, limited_results)
        if not limited_results:
            return NO_RESULTS_MESSAGE
        self._remember_search(query)
        return "\n\n".join(
            self._format_result(position, result)
            for position, result in enumerate(limited_results, start=1)
        )

    def _previous_search_day(self, query: str) -> date | None:
        """A broken history file must not stop the capybara from searching."""
        if self._search_history is None:
            return None
        try:
            return self._search_history.last_searched_on(query)
        except SearchHistoryError as error:
            logger.warning("Could not check the search history: %s", error)
            return None

    def _remember_search(self, query: str) -> None:
        """Only searches that found something are remembered: an empty one may work later."""
        if self._search_history is None:
            return
        try:
            self._search_history.record(query, self._today())
        except SearchHistoryError as error:
            logger.warning("Could not record the search: %s", error)

    def _log_search(self, query: str, results: list[SearchResult]) -> None:
        """Every search that ran goes to the log, even an empty one; a failure is only logged."""
        if self._search_log is None:
            return
        record = SearchRecord(
            searched_at=self._now(),
            query=query,
            results=tuple(FoundPage(title=result.title, url=result.url) for result in results),
        )
        try:
            self._search_log.append(record)
        except SearchLogError as error:
            logger.warning("Could not write the search to the log: %s", error)

    def _format_result(self, position: int, result: SearchResult) -> str:
        return f"{position}. {result.title}\n{result.url}\n{self._shorten(result.snippet)}"

    def _shorten(self, snippet: str) -> str:
        if len(snippet) <= self._max_snippet_length:
            return snippet
        cut_length = self._max_snippet_length - len(ELLIPSIS)
        return snippet[:cut_length].rstrip() + ELLIPSIS
