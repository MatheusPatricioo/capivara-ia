import logging
from collections.abc import Callable
from datetime import date, datetime

from pydantic import Field

from src.application.tools.seen_sources import SeenSources
from src.application.tools.tool_arguments import (
    NonEmptyText,
    ToolArguments,
    parse_arguments,
    tool_parameters,
)
from src.domain.language_model import ToolDefinition
from src.domain.search_history import SearchHistory, SearchHistoryError
from src.domain.search_log import FoundPage, SearchLog, SearchLogError, SearchRecord
from src.domain.tool import ToolError
from src.domain.web_search import SearchResult, WebSearcher, WebSearchError

DEFAULT_MAX_RESULTS = 5
DEFAULT_MAX_SNIPPET_LENGTH = 300
# The two messages below are written as what she sees or remembers, in Portuguese, never
# as someone giving orders: worded as an order, the model answered "tá bom, tá bom" as if
# her creator had told her what to research. Each one also says what she can do right now,
# because a search she only announces never happens (the cycle ends with her answer).

# Says right away that an empty search leaves nothing to save, so the model does not
# try save_discovery without sources and burn the remaining steps on refusals.
NO_RESULTS_MESSAGE = (
    "(A busca voltou vazia: nada apareceu na tela, então dessa vez não há o que guardar. "
    "Ninguém falou com você, foi só a busca. Se quiser, tente agora com outras palavras; "
    "se não, conte do seu jeito como foi.)"
)
ELLIPSIS = "..."
ALREADY_SEARCHED_PREFIX = "(Na tela do computador: essa busca já está no seu histórico"
ALREADY_SEARCHED_MESSAGE = (
    ALREADY_SEARCHED_PREFIX + ", feita em {searched_on}: '{query}'. Isso você já sabe. "
    "Se quiser aprender algo novo, chame web_search agora com outro detalhe ou um assunto "
    "vizinho: dizer que vai pesquisar não pesquisa nada. Se não quiser, conte do seu jeito "
    "o que você já sabe.)"
)
SEARCHED_ON_FORMAT = "%d/%m/%Y"

logger = logging.getLogger(__name__)


class WebSearchArguments(ToolArguments):
    query: NonEmptyText = Field(description="What to search for, written in Brazilian Portuguese.")


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
        follow_up: str = "",
    ) -> None:
        """follow_up goes after real results only, like the reminder to save and tell what
        she learned: after an empty or repeated search there is nothing to tell."""
        self._web_searcher = web_searcher
        self._max_results = max_results
        self._max_snippet_length = max_snippet_length
        self._seen_sources = seen_sources if seen_sources is not None else SeenSources()
        self._search_history = search_history
        self._today = today
        self._search_log = search_log
        self._now = now
        self._follow_up = follow_up

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="web_search",
            description="Searches the web and returns a few results with title, URL and snippet.",
            parameters=tool_parameters(WebSearchArguments),
        )

    def run(self, arguments: dict[str, object]) -> str:
        query = parse_arguments(WebSearchArguments, arguments).query
        searched_on = self._previous_search_day(query)
        if searched_on is not None:
            logger.info("web_search skipped: '%s' was already searched on %s", query, searched_on)
            return ALREADY_SEARCHED_MESSAGE.format(
                query=query, searched_on=searched_on.strftime(SEARCHED_ON_FORMAT)
            )
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
        formatted_results = "\n\n".join(
            self._format_result(position, result)
            for position, result in enumerate(limited_results, start=1)
        )
        if not self._follow_up:
            return formatted_results
        return f"{formatted_results}\n\n{self._follow_up}"

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
