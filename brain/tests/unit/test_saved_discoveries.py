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


def test_finds_the_real_title_by_the_title_in_other_case(
    saved_discoveries: SavedDiscoveries,
) -> None:
    assert saved_discoveries.title_for("o sol") == "O Sol"


def test_finds_the_real_title_by_the_saved_file_name() -> None:
    discoveries = SavedDiscoveries()
    discoveries.remember("Capivaras nadam", "2026-11-23-capivaras-nadam.md")

    assert discoveries.title_for("2026-11-23-capivaras-nadam.md") == "Capivaras nadam"


def test_finds_the_real_title_by_the_file_name_without_extension() -> None:
    discoveries = SavedDiscoveries()
    discoveries.remember("Capivaras nadam", "2026-11-23-capivaras-nadam.md")

    assert discoveries.title_for("2026-11-23-capivaras-nadam") == "Capivaras nadam"


def test_has_no_title_for_an_unknown_name(saved_discoveries: SavedDiscoveries) -> None:
    assert saved_discoveries.title_for("A Lua") is None


def test_a_saved_discovery_starts_without_a_drawing(saved_discoveries: SavedDiscoveries) -> None:
    assert not saved_discoveries.was_drawn("O Sol")


def test_remembers_a_discovery_marked_as_drawn(saved_discoveries: SavedDiscoveries) -> None:
    saved_discoveries.mark_drawn("o sol")

    assert saved_discoveries.was_drawn("O Sol")
