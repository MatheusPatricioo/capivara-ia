from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from src.domain.discovery import Discovery, DiscoveryHeadline, DiscoveryStorageError
from src.infrastructure.markdown_discovery_repository import MarkdownDiscoveryRepository

DISCOVERY = Discovery(
    title="O que capivaras comem?",
    topic="capivaras",
    summary="A gente come capim da beira do rio! Agora entendo minha fome perto do laguinho.",
    sources=("https://example.com/diet", "https://example.com/water"),
    discovered_on=date(2026, 11, 22),
)
EXPECTED_FILE_NAME = "2026-11-22-o-que-capivaras-comem.md"


@pytest.fixture
def discoveries_dir(tmp_path: Path) -> Path:
    return tmp_path / "discoveries"


@pytest.fixture
def repository(discoveries_dir: Path) -> MarkdownDiscoveryRepository:
    return MarkdownDiscoveryRepository(discoveries_dir)


def saved_files(discoveries_dir: Path) -> list[str]:
    return sorted(file.name for file in discoveries_dir.iterdir())


def test_names_the_file_with_the_date_and_the_title_slug(
    repository: MarkdownDiscoveryRepository,
) -> None:
    assert repository.save(DISCOVERY) == EXPECTED_FILE_NAME


def test_creates_the_discoveries_folder_when_it_does_not_exist(
    repository: MarkdownDiscoveryRepository, discoveries_dir: Path
) -> None:
    repository.save(DISCOVERY)

    assert saved_files(discoveries_dir) == [EXPECTED_FILE_NAME]


def test_writes_the_discovery_as_markdown(
    repository: MarkdownDiscoveryRepository, discoveries_dir: Path
) -> None:
    repository.save(DISCOVERY)

    content = (discoveries_dir / EXPECTED_FILE_NAME).read_text(encoding="utf-8")
    assert content == (
        "# O que capivaras comem?\n\n"
        "- **Data:** 2026-11-22\n"
        "- **Tema:** capivaras\n\n"
        "## O que eu descobri\n\n"
        "A gente come capim da beira do rio! Agora entendo minha fome perto do laguinho.\n\n"
        "## Fontes\n\n"
        "- https://example.com/diet\n"
        "- https://example.com/water\n"
    )


def test_removes_accents_and_symbols_from_the_file_name(
    repository: MarkdownDiscoveryRepository,
) -> None:
    file_name = repository.save(replace(DISCOVERY, title="Estrelas & Constelações!!"))

    assert file_name == "2026-11-22-estrelas-constelacoes.md"


def test_uses_a_fallback_name_when_the_title_has_no_letters_or_digits(
    repository: MarkdownDiscoveryRepository,
) -> None:
    file_name = repository.save(replace(DISCOVERY, title="?!*"))

    assert file_name == "2026-11-22-descoberta.md"


def test_does_not_overwrite_a_discovery_with_the_same_name(
    repository: MarkdownDiscoveryRepository, discoveries_dir: Path
) -> None:
    repository.save(DISCOVERY)

    second_file_name = repository.save(replace(DISCOVERY, summary="Outra coisa."))

    assert second_file_name == "2026-11-22-o-que-capivaras-comem-2.md"


def test_keeps_a_relative_traversal_title_inside_the_discoveries_folder(
    repository: MarkdownDiscoveryRepository, discoveries_dir: Path, tmp_path: Path
) -> None:
    repository.save(replace(DISCOVERY, title="../../escaped"))

    assert saved_files(discoveries_dir) == ["2026-11-22-escaped.md"]
    assert saved_files(tmp_path) == ["discoveries"]


def test_keeps_an_absolute_path_title_inside_the_discoveries_folder(
    repository: MarkdownDiscoveryRepository, discoveries_dir: Path
) -> None:
    repository.save(replace(DISCOVERY, title="C:\\Windows\\System32\\evil"))

    assert saved_files(discoveries_dir) == ["2026-11-22-c-windows-system32-evil.md"]


def test_raises_a_storage_error_when_the_folder_cannot_be_created(tmp_path: Path) -> None:
    blocking_file = tmp_path / "not-a-folder"
    blocking_file.write_text("", encoding="utf-8")
    repository = MarkdownDiscoveryRepository(blocking_file)

    with pytest.raises(DiscoveryStorageError):
        repository.save(DISCOVERY)


def test_reads_back_the_title_and_topic_of_a_saved_discovery(
    repository: MarkdownDiscoveryRepository,
) -> None:
    repository.save(DISCOVERY)

    assert repository.latest_headlines(limit=5) == [
        DiscoveryHeadline(title="O que capivaras comem?", topic="capivaras")
    ]


def test_lists_the_most_recent_discoveries_first(
    repository: MarkdownDiscoveryRepository,
) -> None:
    repository.save(replace(DISCOVERY, title="Antiga", discovered_on=date(2026, 11, 20)))
    repository.save(replace(DISCOVERY, title="Nova", discovered_on=date(2026, 11, 23)))

    titles = [headline.title for headline in repository.latest_headlines(limit=5)]

    assert titles == ["Nova", "Antiga"]


def test_lists_at_most_the_requested_number_of_discoveries(
    repository: MarkdownDiscoveryRepository,
) -> None:
    for day in (20, 21, 22):
        repository.save(replace(DISCOVERY, title=f"Dia {day}", discovered_on=date(2026, 11, day)))

    titles = [headline.title for headline in repository.latest_headlines(limit=2)]

    assert titles == ["Dia 22", "Dia 21"]


def test_skips_markdown_files_without_a_title(
    repository: MarkdownDiscoveryRepository, discoveries_dir: Path
) -> None:
    repository.save(DISCOVERY)
    (discoveries_dir / "2026-12-01-nota-solta.md").write_text("só uma nota", encoding="utf-8")

    titles = [headline.title for headline in repository.latest_headlines(limit=5)]

    assert titles == ["O que capivaras comem?"]


def test_lists_nothing_when_the_folder_does_not_exist(
    repository: MarkdownDiscoveryRepository,
) -> None:
    assert repository.latest_headlines(limit=5) == []


def test_raises_a_storage_error_when_a_discovery_cannot_be_read(
    repository: MarkdownDiscoveryRepository, discoveries_dir: Path
) -> None:
    discoveries_dir.mkdir()
    (discoveries_dir / "2026-11-22-quebrada.md").write_bytes(b"\xff\xfe# invalid utf-8 \xff")

    with pytest.raises(DiscoveryStorageError):
        repository.latest_headlines(limit=5)
