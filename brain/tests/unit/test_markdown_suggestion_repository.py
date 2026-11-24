from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from src.domain.world_suggestion import (
    InvalidSuggestionError,
    SavedSuggestion,
    SuggestionStatus,
    SuggestionStorageError,
    WorldSuggestion,
)
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
        "- **Inspirada em:** Vitórias-régias gigantes\n"
        "- **Situação:** pendente\n\n"
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


def requests_of(repository: MarkdownSuggestionRepository) -> list[str]:
    return [saved.suggestion.request for saved in repository.saved_suggestions()]


def test_reads_back_the_saved_suggestion_with_its_file_name(
    repository: MarkdownSuggestionRepository,
) -> None:
    repository.save(SUGGESTION)

    assert repository.saved_suggestions() == [SavedSuggestion(EXPECTED_FILE_NAME, SUGGESTION)]


def test_reads_back_a_reason_with_several_paragraphs(
    repository: MarkdownSuggestionRepository,
) -> None:
    long_reason = replace(SUGGESTION, reason="Primeiro motivo.\n\nSegundo motivo.")
    repository.save(long_reason)

    assert repository.saved_suggestions()[0].suggestion == long_reason


def test_lists_the_suggestions_the_oldest_first(
    repository: MarkdownSuggestionRepository,
) -> None:
    repository.save(replace(SUGGESTION, request="Vaga-lumes no jardim"))
    repository.save(replace(SUGGESTION, suggested_on=date(2026, 11, 20)))

    assert requests_of(repository) == ["Um laguinho com vitórias-régias", "Vaga-lumes no jardim"]


def test_skips_files_that_are_not_suggestions(
    repository: MarkdownSuggestionRepository, suggestions_dir: Path
) -> None:
    repository.save(SUGGESTION)
    (suggestions_dir / "anotacao.md").write_text("# Só um título", encoding="utf-8")

    assert requests_of(repository) == ["Um laguinho com vitórias-régias"]


def test_ignores_files_that_are_not_markdown(
    repository: MarkdownSuggestionRepository, suggestions_dir: Path
) -> None:
    repository.save(SUGGESTION)
    (suggestions_dir / "rascunho.txt").write_text("# Outra coisa", encoding="utf-8")

    assert requests_of(repository) == ["Um laguinho com vitórias-régias"]


def test_lists_nothing_when_nothing_was_suggested_yet(
    repository: MarkdownSuggestionRepository,
) -> None:
    assert repository.saved_suggestions() == []


def test_reads_a_suggestion_without_a_status_line_as_pending(
    repository: MarkdownSuggestionRepository, suggestions_dir: Path
) -> None:
    repository.save(SUGGESTION)
    file_path = suggestions_dir / EXPECTED_FILE_NAME
    content = file_path.read_text(encoding="utf-8")
    file_path.write_text(content.replace("- **Situação:** pendente\n", ""), encoding="utf-8")

    assert repository.saved_suggestions()[0].suggestion.status is SuggestionStatus.PENDING


def test_reads_a_status_typed_by_hand_without_the_accent_as_built(
    repository: MarkdownSuggestionRepository, suggestions_dir: Path
) -> None:
    repository.save(SUGGESTION)
    file_path = suggestions_dir / EXPECTED_FILE_NAME
    content = file_path.read_text(encoding="utf-8")
    file_path.write_text(content.replace("pendente", "Construida"), encoding="utf-8")

    assert repository.saved_suggestions()[0].suggestion.is_built


def test_mark_built_rewrites_the_file_as_built_and_linked_to_the_world_thing(
    repository: MarkdownSuggestionRepository, suggestions_dir: Path
) -> None:
    repository.save(SUGGESTION)

    repository.mark_built(EXPECTED_FILE_NAME, "water_lilies")

    content = (suggestions_dir / EXPECTED_FILE_NAME).read_text(encoding="utf-8")
    assert "- **Situação:** construída\n- **No mundo:** water_lilies\n" in content


def test_mark_built_returns_the_built_suggestion(
    repository: MarkdownSuggestionRepository,
) -> None:
    repository.save(SUGGESTION)

    saved = repository.mark_built(EXPECTED_FILE_NAME, "water_lilies")

    assert saved == SavedSuggestion(EXPECTED_FILE_NAME, SUGGESTION.built("water_lilies"))


def test_mark_built_keeps_the_rest_of_the_suggestion(
    repository: MarkdownSuggestionRepository,
) -> None:
    repository.save(SUGGESTION)

    repository.mark_built(EXPECTED_FILE_NAME)

    assert repository.saved_suggestions()[0].suggestion == SUGGESTION.built()


def test_mark_built_raises_a_storage_error_for_a_missing_file(
    repository: MarkdownSuggestionRepository,
) -> None:
    with pytest.raises(SuggestionStorageError, match="could not read"):
        repository.mark_built("2026-11-24-nao-existe.md")


def test_mark_built_refuses_a_file_outside_the_suggestions_folder(
    repository: MarkdownSuggestionRepository,
) -> None:
    with pytest.raises(SuggestionStorageError, match="outside the suggestions folder"):
        repository.mark_built("../../segredo.md")


def test_mark_built_rejects_an_invalid_world_thing_id(
    repository: MarkdownSuggestionRepository,
) -> None:
    repository.save(SUGGESTION)

    with pytest.raises(InvalidSuggestionError, match="not a world thing id"):
        repository.mark_built(EXPECTED_FILE_NAME, "Vitórias Régias!")
