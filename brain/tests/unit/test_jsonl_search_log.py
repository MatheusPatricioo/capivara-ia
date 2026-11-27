import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.domain.search_log import FoundPage, SearchLogError, SearchRecord
from src.infrastructure.jsonl_search_log import JsonlSearchLog

BRASILIA = timezone(timedelta(hours=-3))
MOON_SEARCH = SearchRecord(
    searched_at=datetime(2026, 11, 23, 10, 15, 2, 999, tzinfo=BRASILIA),
    query="fases da lua",
    results=(
        FoundPage(title="Fases da Lua", url="https://example.com/lua"),
        FoundPage(title="Por que a Lua muda?", url="https://example.com/muda"),
    ),
)
EMPTY_SEARCH = SearchRecord(
    searched_at=datetime(2026, 11, 23, 10, 20, 0, tzinfo=BRASILIA),
    query="corações de polvo",
    results=(),
)
MOON_SEARCH_LINE = {
    "searched_at": "2026-11-23T10:15:02-03:00",
    "query": "fases da lua",
    "results": [
        {"title": "Fases da Lua", "url": "https://example.com/lua"},
        {"title": "Por que a Lua muda?", "url": "https://example.com/muda"},
    ],
}


@pytest.fixture
def log_file(tmp_path: Path) -> Path:
    return tmp_path / "discoveries" / "history" / "searches.jsonl"


@pytest.fixture
def search_log(log_file: Path) -> JsonlSearchLog:
    return JsonlSearchLog(log_file)


def read_lines(log_file: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in log_file.read_text(encoding="utf-8").splitlines()]


def test_writes_the_search_as_one_json_line(search_log: JsonlSearchLog, log_file: Path) -> None:
    search_log.append(MOON_SEARCH)

    assert read_lines(log_file) == [MOON_SEARCH_LINE]


def test_appends_without_erasing_earlier_searches(
    search_log: JsonlSearchLog, log_file: Path
) -> None:
    search_log.append(MOON_SEARCH)

    JsonlSearchLog(log_file).append(EMPTY_SEARCH)

    assert [line["query"] for line in read_lines(log_file)] == [
        "fases da lua",
        "corações de polvo",
    ]


def test_records_a_search_that_found_nothing(search_log: JsonlSearchLog, log_file: Path) -> None:
    search_log.append(EMPTY_SEARCH)

    assert read_lines(log_file)[0] == {
        "searched_at": "2026-11-23T10:20:00-03:00",
        "query": "corações de polvo",
        "results": [],
    }


def test_keeps_accents_readable_in_the_file(search_log: JsonlSearchLog, log_file: Path) -> None:
    search_log.append(EMPTY_SEARCH)

    assert "corações de polvo" in log_file.read_text(encoding="utf-8")


def test_ends_every_search_with_a_line_break(search_log: JsonlSearchLog, log_file: Path) -> None:
    search_log.append(MOON_SEARCH)

    assert log_file.read_bytes().endswith(b"}\n")


def test_raises_search_log_error_when_the_file_cannot_be_written(tmp_path: Path) -> None:
    folder_in_place_of_the_file = tmp_path / "searches.jsonl"
    folder_in_place_of_the_file.mkdir()

    with pytest.raises(SearchLogError):
        JsonlSearchLog(folder_in_place_of_the_file).append(MOON_SEARCH)


def test_reads_back_the_searches_newest_first(search_log: JsonlSearchLog) -> None:
    search_log.append(MOON_SEARCH)
    search_log.append(EMPTY_SEARCH)

    assert [record.query for record in search_log.newest_first()] == [
        "corações de polvo",
        "fases da lua",
    ]


def test_reads_back_the_pages_a_search_found(search_log: JsonlSearchLog) -> None:
    search_log.append(MOON_SEARCH)

    assert search_log.newest_first()[0].results == MOON_SEARCH.results


def test_reading_before_any_search_gives_an_empty_history(search_log: JsonlSearchLog) -> None:
    assert search_log.newest_first() == []


def test_skips_a_broken_line_and_keeps_the_others(
    search_log: JsonlSearchLog, log_file: Path
) -> None:
    log_file.parent.mkdir(parents=True)
    log_file.write_text('{"query": "sem data"\n' + json.dumps(MOON_SEARCH_LINE) + "\n", "utf-8")

    assert [record.query for record in search_log.newest_first()] == ["fases da lua"]


def test_skips_a_line_without_a_query(search_log: JsonlSearchLog, log_file: Path) -> None:
    log_file.parent.mkdir(parents=True)
    log_file.write_text('{"searched_at": "2026-11-23T10:15:02-03:00", "results": []}\n', "utf-8")

    assert search_log.newest_first() == []
