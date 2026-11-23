import logging

from src.application.tools.seen_sources import SeenSources
from src.domain.language_model import ToolDefinition
from src.domain.tool import ToolError
from src.domain.web_search import SearchResult, WebSearcher, WebSearchError

DEFAULT_MAX_RESULTS = 5
DEFAULT_MAX_SNIPPET_LENGTH = 300
# Says right away that an empty search leaves nothing to save, so the model does not
# try save_discovery without sources and burn the remaining steps on refusals.
NO_RESULTS_MESSAGE = (
    "No results found, so there is nothing from this search to save. "
    "Try other words, or move on."
)
ELLIPSIS = "..."

logger = logging.getLogger(__name__)


class WebSearchTool:
    def __init__(
        self,
        web_searcher: WebSearcher,
        max_results: int = DEFAULT_MAX_RESULTS,
        max_snippet_length: int = DEFAULT_MAX_SNIPPET_LENGTH,
        seen_sources: SeenSources | None = None,
    ) -> None:
        self._web_searcher = web_searcher
        self._max_results = max_results
        self._max_snippet_length = max_snippet_length
        self._seen_sources = seen_sources if seen_sources is not None else SeenSources()

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="web_search",
            description="Searches the web and returns a few results with title, URL and snippet.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What to search for."},
                },
                "required": ["query"],
            },
        )

    def run(self, arguments: dict[str, object]) -> str:
        query = arguments.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ToolError("the 'query' argument must be a non-empty text")
        try:
            results = self._web_searcher.search(query.strip(), self._max_results)
        except WebSearchError as error:
            raise ToolError(f"web search failed: {error}") from error
        limited_results = results[: self._max_results]
        self._seen_sources.remember(result.url for result in limited_results)
        logger.info("web_search returned %d result(s)", len(limited_results))
        if not limited_results:
            return NO_RESULTS_MESSAGE
        return "\n\n".join(
            self._format_result(position, result)
            for position, result in enumerate(limited_results, start=1)
        )

    def _format_result(self, position: int, result: SearchResult) -> str:
        return f"{position}. {result.title}\n{result.url}\n{self._shorten(result.snippet)}"

    def _shorten(self, snippet: str) -> str:
        if len(snippet) <= self._max_snippet_length:
            return snippet
        cut_length = self._max_snippet_length - len(ELLIPSIS)
        return snippet[:cut_length].rstrip() + ELLIPSIS
