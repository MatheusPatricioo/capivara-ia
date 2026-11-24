from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from src.domain.world_suggestion import SuggestionStorageError, WorldSuggestion
from src.infrastructure.markdown_suggestion_repository import MarkdownSuggestionRepository

SUGGESTION = WorldSuggestion(
    request="Um laguinho com vitórias-régias",
    reason="Aprendi que as folhas delas aguentam o peso de uma criança!",
    inspired_by="Vitórias-régias gigantes",
    suggested_on=date(2026, 11, 24),
)
EXPECTED_FILE_NAME = "2026-11-24-um-laguinho-com-vitorias-regias.md"


@pytest.fixture
def discoveries_dir(tmp_path: Path) -> Path:
    return tmp_path / "discoveries"


@pytest.fixture
def suggestions_dir(discoveries_dir: Path) -> Path:
    return discoveries_dir / "sugestoes"


@pytest.fixture
def repository(discoveries_dir: Path) -> MarkdownSuggestionRepository:
    return MarkdownSuggestionRepository(discoveries_dir)


def saved_files(folder: Path) -> list[str]:
    return sorted(file.name for file in folder.iterdir())


def test_names_the_file_with_the_date_and_the_request_slug(
    repository: MarkdownSuggestionRepository,
) -> None:
    assert repository.save(SUGGESTION) == EXPECTED_FILE_NAME


def test_saves_inside_the_suggestions_subfolder_of_the_discoveries(
    repository: MarkdownSuggestionRepository, discoveries_dir: Path, suggestions_dir: Path
) -> None:
    repository.save(SUGGESTION)

    assert saved_files(discoveries_dir) == ["sugestoes"]
    assert saved_files(suggestions_dir) == [EXPECTED_FILE_NAME]


def test_writes_the_suggestion_as_markdown(
    repository: MarkdownSuggestionRepository, suggestions_dir: Path
) -> None:
    repository.save(SUGGESTION)

    content = (suggestions_dir / EXPECTED_FILE_NAME).read_text(encoding="utf-8")
    assert content == (
        "# Um laguinho com vitórias-régias\n\n"
        "- **Data:** 2026-11-24\n"
        "- **Inspirada em:** Vitórias-régias gigantes\n\n"
        "## Por que eu quero\n\n"
        "Aprendi que as folhas delas aguentam o peso de uma criança!\n"
    )


def test_does_not_overwrite_a_suggestion_with_the_same_request(
    repository: MarkdownSuggestionRepository,
) -> None:
    repository.save(SUGGESTION)

    second_file_name = repository.save(replace(SUGGESTION, reason="Outro motivo."))

    assert second_file_name == "2026-11-24-um-laguinho-com-vitorias-regias-2.md"


def test_keeps_a_traversal_request_inside_the_suggestions_folder(
    repository: MarkdownSuggestionRepository, suggestions_dir: Path, tmp_path: Path
) -> None:
    repository.save(replace(SUGGESTION, request="../../escaped"))

    assert saved_files(suggestions_dir) == ["2026-11-24-escaped.md"]
    assert saved_files(tmp_path) == ["discoveries"]


def test_raises_a_storage_error_when_the_folder_cannot_be_created(tmp_path: Path) -> None:
    blocking_file = tmp_path / "not-a-folder"
    blocking_file.write_text("", encoding="utf-8")
    repository = MarkdownSuggestionRepository(blocking_file)

    with pytest.raises(SuggestionStorageError, match="could not save"):
        repository.save(SUGGESTION)
