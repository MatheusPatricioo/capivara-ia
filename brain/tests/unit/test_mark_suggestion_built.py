from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from src.domain.world_suggestion import WorldSuggestion
from src.infrastructure.markdown_suggestion_repository import MarkdownSuggestionRepository
from src.mark_suggestion_built import FAILURE, SUCCESS, run

SUGGESTION = WorldSuggestion(
    request="Um laguinho com vitórias-régias",
    reason="As folhas aguentam uma criança!",
    inspired_by="Vitória-régia gigante",
    suggested_on=date(2026, 11, 24),
)
FILE_NAME = "2026-11-24-um-laguinho-com-vitorias-regias.md"


@pytest.fixture
def repository(tmp_path: Path) -> MarkdownSuggestionRepository:
    repository = MarkdownSuggestionRepository(tmp_path)
    repository.save(SUGGESTION)
    return repository


def test_without_a_file_lists_the_suggestions_waiting(
    repository: MarkdownSuggestionRepository, capsys: pytest.CaptureFixture[str]
) -> None:
    run([], repository)

    assert f"{FILE_NAME}  (Um laguinho com vitórias-régias)" in capsys.readouterr().out


def test_the_list_leaves_out_suggestions_already_built(
    repository: MarkdownSuggestionRepository, capsys: pytest.CaptureFixture[str]
) -> None:
    repository.save(replace(SUGGESTION, request="Vaga-lumes no jardim").built())

    run([], repository)

    assert "Vaga-lumes no jardim" not in capsys.readouterr().out


def test_says_so_when_nothing_is_waiting(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    run([], MarkdownSuggestionRepository(tmp_path))

    assert capsys.readouterr().out == "Nenhuma sugestão esperando.\n"


def test_marks_the_file_as_built_with_the_world_thing(
    repository: MarkdownSuggestionRepository,
) -> None:
    exit_code = run([FILE_NAME, "--thing-id", "water_lilies"], repository)

    assert exit_code == SUCCESS
    assert repository.saved_suggestions()[0].suggestion == SUGGESTION.built("water_lilies")


def test_tells_where_she_will_recognize_the_wish(
    repository: MarkdownSuggestionRepository, capsys: pytest.CaptureFixture[str]
) -> None:
    run([FILE_NAME, "--thing-id", "water_lilies"], repository)

    assert "quando passar por water_lilies" in capsys.readouterr().out


def test_fails_with_a_message_for_a_missing_file(
    repository: MarkdownSuggestionRepository, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = run(["2026-11-24-nao-existe.md"], repository)

    assert exit_code == FAILURE
    assert "Não consegui marcar a sugestão" in capsys.readouterr().err


def test_fails_with_a_message_for_an_invalid_thing_id(
    repository: MarkdownSuggestionRepository, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = run([FILE_NAME, "--thing-id", "Vitórias Régias"], repository)

    assert exit_code == FAILURE
    assert "not a world thing id" in capsys.readouterr().err
