import json
from datetime import date
from pathlib import Path

import pytest

from src.domain.search_history import SearchHistoryError
from src.infrastructure.json_search_history import JsonSearchHistory

SEARCH_DAY = date(2026, 11, 23)


@pytest.fixture
def history_file(tmp_path: Path) -> Path:
    return tmp_path / "discoveries" / "search-history.json"


@pytest.fixture
def history(history_file: Path) -> JsonSearchHistory:
    return JsonSearchHistory(history_file)


def test_knows_nothing_before_the_first_search(history: JsonSearchHistory) -> None:
    assert history.last_searched_on("estrelas") is None


def test_remembers_the_day_of_a_recorded_search(history: JsonSearchHistory) -> None:
    history.record("estrelas", SEARCH_DAY)

    assert history.last_searched_on("estrelas") == SEARCH_DAY


def test_finds_the_same_search_written_differently(history: JsonSearchHistory) -> None:
    history.record("Buracos negros!", SEARCH_DAY)

    assert history.last_searched_on("os buracos-negros") == SEARCH_DAY


def test_keeps_the_history_between_instances(history_file: Path) -> None:
    JsonSearchHistory(history_file).record("estrelas", SEARCH_DAY)

    assert JsonSearchHistory(history_file).last_searched_on("estrelas") == SEARCH_DAY


def test_stores_the_original_query_so_the_file_stays_readable(
    history: JsonSearchHistory, history_file: Path
) -> None:
    history.record("Buracos negros!", SEARCH_DAY)

    assert json.loads(history_file.read_text(encoding="utf-8")) == {
        "buracos negros": {"query": "Buracos negros!", "searched_on": "2026-11-23"}
    }


def test_raises_a_history_error_when_the_file_is_not_json(
    history: JsonSearchHistory, history_file: Path
) -> None:
    history_file.parent.mkdir(parents=True)
    history_file.write_text("not json", encoding="utf-8")

    with pytest.raises(SearchHistoryError):
        history.last_searched_on("estrelas")


def test_raises_a_history_error_when_an_entry_has_no_valid_date(
    history: JsonSearchHistory, history_file: Path
) -> None:
    history_file.parent.mkdir(parents=True)
    history_file.write_text('{"estrelas": {"query": "estrelas"}}', encoding="utf-8")

    with pytest.raises(SearchHistoryError):
        history.last_searched_on("estrelas")
