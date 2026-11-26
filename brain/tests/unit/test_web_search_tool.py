import logging
from datetime import date, datetime, timedelta, timezone

import pytest

from src.application.tools.seen_sources import SeenSources
from src.application.tools.web_search_tool import WebSearchTool
from src.domain.search_history import SearchHistoryError
from src.domain.search_log import FoundPage, SearchLogError, SearchRecord
from src.domain.tool import ToolError
from src.domain.web_search import SearchResult, WebSearchError

QUERY = "capybara diet"
MAX_RESULTS = 2
MAX_SNIPPET_LENGTH = 20
WEB_SEARCH_TOOL_LOGGER = "src.application.tools.web_search_tool"
FOLLOW_UP = "(Lembrete: conte o que descobriu.)"
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

    assert output.startswith("(A busca voltou vazia")


def test_an_empty_search_does_not_get_the_follow_up() -> None:
    tool = WebSearchTool(FakeWebSearcher([]), follow_up=FOLLOW_UP)

    output = tool.run({"query": QUERY})

    assert FOLLOW_UP not in output


def test_real_results_end_with_the_follow_up() -> None:
    tool = WebSearchTool(FakeWebSearcher([GRASS_RESULT]), follow_up=FOLLOW_UP)

    output = tool.run({"query": QUERY})

    assert output.endswith(f"\n\n{FOLLOW_UP}")


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


SEARCH_DAY = date(2026, 11, 23)


class InMemorySearchHistory:
    """Keeps searches in a dict, keyed by the exact query (normalization is tested elsewhere)."""

    def __init__(self) -> None:
        self.days_by_query: dict[str, date] = {}

    def last_searched_on(self, query: str) -> date | None:
        return self.days_by_query.get(query)

    def record(self, query: str, searched_on: date) -> None:
        self.days_by_query[query] = searched_on


class BrokenSearchHistory:
    def last_searched_on(self, query: str) -> date | None:
        raise SearchHistoryError("disk unplugged")

    def record(self, query: str, searched_on: date) -> None:
        raise SearchHistoryError("disk unplugged")


@pytest.fixture
def search_history() -> InMemorySearchHistory:
    return InMemorySearchHistory()


@pytest.fixture
def web_searcher() -> FakeWebSearcher:
    return FakeWebSearcher([GRASS_RESULT])


def build_tool_with_history(
    web_searcher: FakeWebSearcher, search_history: InMemorySearchHistory | BrokenSearchHistory
) -> WebSearchTool:
    return WebSearchTool(web_searcher, search_history=search_history, today=lambda: SEARCH_DAY)


def test_records_a_search_that_found_results(
    web_searcher: FakeWebSearcher, search_history: InMemorySearchHistory
) -> None:
    build_tool_with_history(web_searcher, search_history).run({"query": QUERY})

    assert search_history.days_by_query == {QUERY: SEARCH_DAY}


def test_does_not_record_a_search_that_found_nothing(
    search_history: InMemorySearchHistory,
) -> None:
    build_tool_with_history(FakeWebSearcher([]), search_history).run({"query": QUERY})

    assert search_history.days_by_query == {}


def test_does_not_search_the_web_again_for_a_repeated_search(
    web_searcher: FakeWebSearcher, search_history: InMemorySearchHistory
) -> None:
    search_history.record(QUERY, SEARCH_DAY)

    build_tool_with_history(web_searcher, search_history).run({"query": QUERY})

    assert web_searcher.received_searches == []


def test_tells_the_model_when_it_already_searched_the_same_thing(
    web_searcher: FakeWebSearcher, search_history: InMemorySearchHistory
) -> None:
    search_history.record(QUERY, SEARCH_DAY)

    output = build_tool_with_history(web_searcher, search_history).run({"query": QUERY})

    assert output.startswith(
        "(Na tela do computador: essa busca já está no seu histórico, "
        f"feita em 23/11/2026: '{QUERY}'"
    )


def test_a_repeated_search_does_not_get_the_follow_up(
    web_searcher: FakeWebSearcher, search_history: InMemorySearchHistory
) -> None:
    search_history.record(QUERY, SEARCH_DAY)
    tool = WebSearchTool(web_searcher, search_history=search_history, follow_up=FOLLOW_UP)

    output = tool.run({"query": QUERY})

    assert FOLLOW_UP not in output


def test_still_searches_when_the_history_is_broken(web_searcher: FakeWebSearcher) -> None:
    build_tool_with_history(web_searcher, BrokenSearchHistory()).run({"query": QUERY})

    assert web_searcher.received_searches == [(QUERY, 5)]


def test_logs_a_warning_when_the_history_is_broken(
    web_searcher: FakeWebSearcher, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.WARNING, logger=WEB_SEARCH_TOOL_LOGGER)

    build_tool_with_history(web_searcher, BrokenSearchHistory()).run({"query": QUERY})

    assert caplog.messages == [
        "Could not check the search history: disk unplugged",
        "Could not record the search: disk unplugged",
    ]


SEARCH_MOMENT = datetime(2026, 11, 23, 10, 15, 2, tzinfo=timezone(timedelta(hours=-3)))


class InMemorySearchLog:
    def __init__(self) -> None:
        self.records: list[SearchRecord] = []

    def append(self, record: SearchRecord) -> None:
        self.records.append(record)


class BrokenSearchLog:
    def append(self, record: SearchRecord) -> None:
        raise SearchLogError("disk unplugged")


@pytest.fixture
def search_log() -> InMemorySearchLog:
    return InMemorySearchLog()


def build_tool_with_log(
    web_searcher: FakeWebSearcher | OfflineWebSearcher,
    search_log: InMemorySearchLog | BrokenSearchLog,
    search_history: InMemorySearchHistory | None = None,
) -> WebSearchTool:
    return WebSearchTool(
        web_searcher,
        max_results=MAX_RESULTS,
        search_history=search_history,
        today=lambda: SEARCH_DAY,
        search_log=search_log,
        now=lambda: SEARCH_MOMENT,
    )


def test_logs_the_search_with_its_moment_query_and_pages(
    search_log: InMemorySearchLog,
) -> None:
    tool = build_tool_with_log(FakeWebSearcher([GRASS_RESULT, WATER_RESULT]), search_log)

    tool.run({"query": QUERY})

    assert search_log.records == [
        SearchRecord(
            searched_at=SEARCH_MOMENT,
            query=QUERY,
            results=(
                FoundPage(title="What capybaras eat", url="https://example.com/diet"),
                FoundPage(title="Capybaras and water", url="https://example.com/water"),
            ),
        )
    ]


def test_logs_only_the_pages_shown_to_the_model(search_log: InMemorySearchLog) -> None:
    tool = build_tool_with_log(
        FakeWebSearcher([GRASS_RESULT, WATER_RESULT, EXTRA_RESULT]), search_log
    )

    tool.run({"query": QUERY})

    assert len(search_log.records[0].results) == MAX_RESULTS


def test_logs_a_search_that_found_nothing(search_log: InMemorySearchLog) -> None:
    build_tool_with_log(FakeWebSearcher([]), search_log).run({"query": QUERY})

    assert search_log.records == [SearchRecord(SEARCH_MOMENT, QUERY, results=())]


def test_does_not_log_a_search_skipped_because_it_was_already_done(
    web_searcher: FakeWebSearcher,
    search_log: InMemorySearchLog,
    search_history: InMemorySearchHistory,
) -> None:
    search_history.record(QUERY, SEARCH_DAY)

    build_tool_with_log(web_searcher, search_log, search_history).run({"query": QUERY})

    assert search_log.records == []


def test_does_not_log_a_search_that_failed(search_log: InMemorySearchLog) -> None:
    with pytest.raises(ToolError):
        build_tool_with_log(OfflineWebSearcher(), search_log).run({"query": QUERY})

    assert search_log.records == []


def test_still_returns_the_results_when_the_log_is_broken(web_searcher: FakeWebSearcher) -> None:
    output = build_tool_with_log(web_searcher, BrokenSearchLog()).run({"query": QUERY})

    assert output.startswith("1. What capybaras eat")


def test_warns_when_the_search_cannot_be_logged(
    web_searcher: FakeWebSearcher, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.WARNING, logger=WEB_SEARCH_TOOL_LOGGER)

    build_tool_with_log(web_searcher, BrokenSearchLog()).run({"query": QUERY})

    assert caplog.messages == ["Could not write the search to the log: disk unplugged"]
