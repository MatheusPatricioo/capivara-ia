"""Discoveries saved as Markdown before the memory existed can be recalled after the backfill."""

from datetime import date
from pathlib import Path

import pytest

from src.application.backfill_memory import BackfillMemory, BackfillReport
from src.domain.discovery import Discovery
from src.infrastructure.markdown_discovery_repository import MarkdownDiscoveryRepository
from tests.fakes.in_memory_discovery_memory import InMemoryDiscoveryMemory, WordCountEmbedder

HAND_WRITTEN_NOTE = "lembrete.md"
CAPYBARAS = Discovery(
    title="Capivaras nadam",
    topic="capivaras",
    summary="Capivaras prendem a respiração por cinco minutos.\n\nE dormem na água!",
    sources=("https://example.com/swim",),
    discovered_on=date(2026, 11, 22),
)
FIREFLIES = Discovery(
    title="Vaga-lumes",
    topic="insetos",
    summary="Vaga-lumes brilham para se comunicar.",
    sources=(),
    discovered_on=date(2026, 11, 23),
)


@pytest.fixture
def memory() -> InMemoryDiscoveryMemory:
    return InMemoryDiscoveryMemory(WordCountEmbedder(["capivaras", "vaga-lumes", "brilham"]))


@pytest.fixture
def report(tmp_path: Path, memory: InMemoryDiscoveryMemory) -> BackfillReport:
    repository = MarkdownDiscoveryRepository(tmp_path)
    repository.save(CAPYBARAS)
    repository.save(FIREFLIES)
    (tmp_path / HAND_WRITTEN_NOTE).write_text("comprar capim", encoding="utf-8")
    return BackfillMemory(repository, memory).execute()


def test_a_discovery_saved_before_the_memory_can_be_recalled(
    report: BackfillReport, memory: InMemoryDiscoveryMemory
) -> None:
    [remembered] = memory.recall("vaga-lumes que brilham", limit=1)

    assert remembered.discovery == FIREFLIES


def test_the_whole_discovery_comes_back_from_the_markdown(
    report: BackfillReport, memory: InMemoryDiscoveryMemory
) -> None:
    [remembered] = memory.recall("capivaras", limit=1)

    assert remembered.discovery == CAPYBARAS


def test_a_hand_written_note_is_skipped(report: BackfillReport) -> None:
    assert [skipped.file_name for skipped in report.skipped] == [HAND_WRITTEN_NOTE]


def test_every_saved_discovery_is_reported_as_remembered(report: BackfillReport) -> None:
    assert report.remembered == ("2026-11-22-capivaras-nadam.md", "2026-11-23-vaga-lumes.md")
