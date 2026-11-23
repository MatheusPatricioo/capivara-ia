import logging

import pytest

from src.application.tools.seen_sources import SeenSources
from src.application.tools.web_search_tool import WebSearchTool
from src.domain.tool import ToolError
from src.domain.web_search import SearchResult, WebSearchError

QUERY = "capybara diet"
MAX_RESULTS = 2
MAX_SNIPPET_LENGTH = 20
WEB_SEARCH_TOOL_LOGGER = "src.application.tools.web_search_tool"
GRASS_RESULT = SearchResult(
    title="What capybaras eat",
    url="https://example.com/diet",
    snippet="Mostly grass.",
)
WATER_RESULT = SearchResult(
    title="Capybaras and water",
    url="https://example.com/water",
    snippet="They love ponds.",
)
EXTRA_RESULT = SearchResult(
    title="Extra result",
    url="https://example.com/extra",
    snippet="Should be left out.",
)
LONG_SNIPPET_RESULT = SearchResult(
    title="Long article",
    url="https://example.com/long",
    snippet="Capybaras are the largest rodents in the world.",
)


class FakeWebSearcher:
    """Returns canned results and records every search it receives."""

    def __init__(self, results: list[SearchResult]) -> None:
        self._results = results
        self.received_searches: list[tuple[str, int]] = []

    def search(self, query: str, max_results: int) -> list[SearchResult]:
        self.received_searches.append((query, max_results))
        return self._results


class OfflineWebSearcher:
    def search(self, query: str, max_results: int) -> list[SearchResult]:
        raise WebSearchError("connection timed out")


def build_tool(results: list[SearchResult]) -> WebSearchTool:
    return WebSearchTool(
        FakeWebSearcher(results),
        max_results=MAX_RESULTS,
        max_snippet_length=MAX_SNIPPET_LENGTH,
    )


@pytest.fixture
def fake_web_searcher() -> FakeWebSearcher:
    return FakeWebSearcher([GRASS_RESULT, WATER_RESULT])


@pytest.fixture
def web_search_tool(fake_web_searcher: FakeWebSearcher) -> WebSearchTool:
    return WebSearchTool(
        fake_web_searcher,
        max_results=MAX_RESULTS,
        max_snippet_length=MAX_SNIPPET_LENGTH,
    )


def test_definition_is_named_web_search(web_search_tool: WebSearchTool) -> None:
    assert web_search_tool.definition.name == "web_search"


def test_definition_requires_a_query(web_search_tool: WebSearchTool) -> None:
    assert web_search_tool.definition.parameters["required"] == ["query"]


def test_searches_for_the_query_with_the_result_limit(
    web_search_tool: WebSearchTool, fake_web_searcher: FakeWebSearcher
) -> None:
    web_search_tool.run({"query": f"  {QUERY}  "})

    assert fake_web_searcher.received_searches == [(QUERY, MAX_RESULTS)]


def test_formats_results_as_a_numbered_list(web_search_tool: WebSearchTool) -> None:
    output = web_search_tool.run({"query": QUERY})

    assert output == (
        "1. What capybaras eat\nhttps://example.com/diet\nMostly grass.\n\n"
        "2. Capybaras and water\nhttps://example.com/water\nThey love ponds."
    )


def test_keeps_only_the_maximum_number_of_results() -> None:
    tool = build_tool([GRASS_RESULT, WATER_RESULT, EXTRA_RESULT])

    output = tool.run({"query": QUERY})

    assert EXTRA_RESULT.url not in output


def test_shortens_long_snippets() -> None:
    tool = build_tool([LONG_SNIPPET_RESULT])

    output = tool.run({"query": QUERY})

    assert output.endswith("\nCapybaras are the...")


def test_remembers_the_urls_it_showed_to_the_model(fake_web_searcher: FakeWebSearcher) -> None:
    seen_sources = SeenSources()
    tool = WebSearchTool(fake_web_searcher, seen_sources=seen_sources)

    tool.run({"query": QUERY})

    assert seen_sources.contains(GRASS_RESULT.url)


def test_does_not_remember_urls_left_out_by_the_limit() -> None:
    seen_sources = SeenSources()
    tool = WebSearchTool(
        FakeWebSearcher([GRASS_RESULT, WATER_RESULT, EXTRA_RESULT]),
        max_results=MAX_RESULTS,
        seen_sources=seen_sources,
    )

    tool.run({"query": QUERY})

    assert not seen_sources.contains(EXTRA_RESULT.url)


def test_says_there_is_nothing_to_save_when_there_are_no_results() -> None:
    tool = build_tool([])

    output = tool.run({"query": QUERY})

    assert output.startswith("No results found, so there is nothing from this search to save")


def test_logs_how_many_results_were_returned(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger=WEB_SEARCH_TOOL_LOGGER)
    tool = build_tool([GRASS_RESULT, WATER_RESULT, EXTRA_RESULT])

    tool.run({"query": QUERY})

    assert "web_search returned 2 result(s)" in caplog.messages


def test_logs_zero_results_when_nothing_is_found(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger=WEB_SEARCH_TOOL_LOGGER)
    tool = build_tool([])

    tool.run({"query": QUERY})

    assert "web_search returned 0 result(s)" in caplog.messages


def test_rejects_a_missing_query(web_search_tool: WebSearchTool) -> None:
    with pytest.raises(ToolError):
        web_search_tool.run({})


def test_rejects_a_blank_query(web_search_tool: WebSearchTool) -> None:
    with pytest.raises(ToolError):
        web_search_tool.run({"query": "   "})


def test_rejects_a_query_that_is_not_text(web_search_tool: WebSearchTool) -> None:
    with pytest.raises(ToolError):
        web_search_tool.run({"query": 42})


def test_turns_search_failures_into_tool_errors() -> None:
    tool = WebSearchTool(OfflineWebSearcher())

    with pytest.raises(ToolError, match="connection timed out"):
        tool.run({"query": QUERY})
