from datetime import date

import pytest

from src.application.backfill_memory import BackfillMemory, SkippedFile
from src.domain.discovery import Discovery, DiscoveryStorageError
from src.domain.discovery_memory import DiscoveryMemoryError, RememberedDiscovery
from tests.fakes.in_memory_discovery_memory import InMemoryDiscoveryMemory, WordCountEmbedder

MOON_FILE = "2026-11-22-fases-da-lua.md"
STARS_FILE = "2026-11-23-constelacoes.md"
BROKEN_FILE = "2026-11-23-quebrada.md"
MOON = Discovery(
    title="Fases da lua",
    topic="lua",
    summary="A lua tem fases",
    sources=("https://example.com/lua",),
    discovered_on=date(2026, 11, 22),
)
STARS = Discovery(
    title="Constelações",
    topic="estrelas",
    summary="Estrelas formam constelações",
    sources=("https://example.com/estrelas",),
    discovered_on=date(2026, 11, 23),
)


class FakeDiscoveryArchive:
    """Saved discoveries by file name; None stands for a file that cannot be read."""

    def __init__(self, files: dict[str, Discovery | None]) -> None:
        self._files = files

    def saved_file_names(self) -> list[str]:
        return sorted(self._files)

    def read(self, file_name: str) -> Discovery:
        discovery = self._files[file_name]
        if discovery is None:
            raise DiscoveryStorageError(f"{file_name} has no summary")
        return discovery


class OfflineDiscoveryMemory:
    def remember(self, file_name: str, discovery: Discovery) -> None:
        raise DiscoveryMemoryError("database offline")

    def recall(self, text: str, limit: int) -> list[RememberedDiscovery]:
        raise DiscoveryMemoryError("database offline")


@pytest.fixture
def memory() -> InMemoryDiscoveryMemory:
    return InMemoryDiscoveryMemory(WordCountEmbedder(["lua", "estrelas", "constelações"]))


@pytest.fixture
def archive() -> FakeDiscoveryArchive:
    return FakeDiscoveryArchive({MOON_FILE: MOON, STARS_FILE: STARS, BROKEN_FILE: None})


@pytest.fixture
def backfill(archive: FakeDiscoveryArchive, memory: InMemoryDiscoveryMemory) -> BackfillMemory:
    return BackfillMemory(archive, memory)


def test_puts_every_readable_discovery_in_the_memory(
    backfill: BackfillMemory, memory: InMemoryDiscoveryMemory
) -> None:
    backfill.execute()

    remembered = memory.recall("lua estrelas constelações", limit=5)
    assert {item.discovery for item in remembered} == {MOON, STARS}


def test_reports_the_remembered_files_the_oldest_first(backfill: BackfillMemory) -> None:
    report = backfill.execute()

    assert report.remembered == (MOON_FILE, STARS_FILE)


def test_reports_an_unreadable_file_as_skipped_with_its_reason(
    backfill: BackfillMemory,
) -> None:
    report = backfill.execute()

    assert report.skipped == (SkippedFile(BROKEN_FILE, f"{BROKEN_FILE} has no summary"),)


def test_running_twice_does_not_duplicate_the_memories(
    backfill: BackfillMemory, memory: InMemoryDiscoveryMemory
) -> None:
    backfill.execute()
    backfill.execute()

    assert len(memory.recall("lua", limit=10)) == 2


def test_reports_nothing_when_there_are_no_saved_discoveries(
    memory: InMemoryDiscoveryMemory,
) -> None:
    report = BackfillMemory(FakeDiscoveryArchive({}), memory).execute()

    assert (report.remembered, report.skipped) == ((), ())


def test_stops_with_a_memory_error_when_the_memory_is_offline(
    archive: FakeDiscoveryArchive,
) -> None:
    backfill = BackfillMemory(archive, OfflineDiscoveryMemory())

    with pytest.raises(DiscoveryMemoryError):
        backfill.execute()
