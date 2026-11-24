import logging
from datetime import date

import pytest

from src.application.remembering_discovery_repository import RememberingDiscoveryRepository
from src.domain.discovery import Discovery, DiscoveryStorageError
from src.domain.discovery_memory import DiscoveryMemoryError, RememberedDiscovery
from tests.fakes.in_memory_discovery_memory import InMemoryDiscoveryMemory, WordCountEmbedder

FILE_NAME = "2026-11-24-fases-da-lua.md"
MOON = Discovery(
    title="Fases da lua",
    topic="lua",
    summary="A lua tem fases",
    sources=("https://example.com/lua",),
    discovered_on=date(2026, 11, 24),
)


class FixedNameDiscoveryRepository:
    """Saves nothing on disk and always answers the same file name."""

    def __init__(self) -> None:
        self.saved: list[Discovery] = []

    def save(self, discovery: Discovery) -> str:
        self.saved.append(discovery)
        return FILE_NAME


class FullDiskDiscoveryRepository:
    def save(self, discovery: Discovery) -> str:
        raise DiscoveryStorageError("disk full")


class OfflineDiscoveryMemory:
    def remember(self, file_name: str, discovery: Discovery) -> None:
        raise DiscoveryMemoryError("database offline")

    def recall(self, text: str, limit: int) -> list[RememberedDiscovery]:
        raise DiscoveryMemoryError("database offline")


@pytest.fixture
def memory() -> InMemoryDiscoveryMemory:
    return InMemoryDiscoveryMemory(WordCountEmbedder(["lua", "fases"]))


@pytest.fixture
def inner_repository() -> FixedNameDiscoveryRepository:
    return FixedNameDiscoveryRepository()


@pytest.fixture
def repository(
    inner_repository: FixedNameDiscoveryRepository, memory: InMemoryDiscoveryMemory
) -> RememberingDiscoveryRepository:
    return RememberingDiscoveryRepository(inner_repository, memory)


@pytest.fixture
def repository_with_offline_memory(
    inner_repository: FixedNameDiscoveryRepository,
) -> RememberingDiscoveryRepository:
    return RememberingDiscoveryRepository(inner_repository, OfflineDiscoveryMemory())


def test_save_returns_the_name_from_the_wrapped_repository(
    repository: RememberingDiscoveryRepository,
) -> None:
    assert repository.save(MOON) == FILE_NAME


def test_save_stores_the_discovery_in_the_wrapped_repository(
    repository: RememberingDiscoveryRepository, inner_repository: FixedNameDiscoveryRepository
) -> None:
    repository.save(MOON)

    assert inner_repository.saved == [MOON]


def test_save_puts_the_discovery_in_the_memory(
    repository: RememberingDiscoveryRepository, memory: InMemoryDiscoveryMemory
) -> None:
    repository.save(MOON)

    [remembered] = memory.recall("fases da lua", limit=1)
    assert remembered.discovery == MOON


def test_save_still_returns_the_name_when_the_memory_is_offline(
    repository_with_offline_memory: RememberingDiscoveryRepository,
) -> None:
    assert repository_with_offline_memory.save(MOON) == FILE_NAME


def test_save_logs_a_warning_when_the_memory_is_offline(
    repository_with_offline_memory: RememberingDiscoveryRepository,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        repository_with_offline_memory.save(MOON)

    assert f"Saved {FILE_NAME}, but could not remember it: database offline" in caplog.text


def test_save_remembers_nothing_when_the_wrapped_repository_fails(
    memory: InMemoryDiscoveryMemory,
) -> None:
    repository = RememberingDiscoveryRepository(FullDiskDiscoveryRepository(), memory)

    with pytest.raises(DiscoveryStorageError):
        repository.save(MOON)

    assert memory.recall("lua", limit=1) == []
