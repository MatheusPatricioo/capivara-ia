import pytest

from src.application.tools.saved_discoveries import SavedDiscoveries


@pytest.fixture
def saved_discoveries() -> SavedDiscoveries:
    discoveries = SavedDiscoveries()
    discoveries.remember("O Sol")
    return discoveries


def test_contains_a_remembered_title(saved_discoveries: SavedDiscoveries) -> None:
    assert saved_discoveries.contains("O Sol")


def test_ignores_case_and_surrounding_spaces(saved_discoveries: SavedDiscoveries) -> None:
    assert saved_discoveries.contains("  o sol ")


def test_does_not_contain_an_unknown_title(saved_discoveries: SavedDiscoveries) -> None:
    assert not saved_discoveries.contains("A Lua")


def test_a_saved_discovery_starts_without_a_drawing(saved_discoveries: SavedDiscoveries) -> None:
    assert not saved_discoveries.was_drawn("O Sol")


def test_remembers_a_discovery_marked_as_drawn(saved_discoveries: SavedDiscoveries) -> None:
    saved_discoveries.mark_drawn("o sol")

    assert saved_discoveries.was_drawn("O Sol")
