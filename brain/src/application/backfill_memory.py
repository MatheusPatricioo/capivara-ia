import logging
from dataclasses import dataclass

from src.domain.discovery import DiscoveryArchive, DiscoveryStorageError
from src.domain.discovery_memory import DiscoveryMemory

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SkippedFile:
    file_name: str
    reason: str


@dataclass(frozen=True)
class BackfillReport:
    remembered: tuple[str, ...]
    skipped: tuple[SkippedFile, ...]


class BackfillMemory:
    """Puts the discoveries saved before the long-term memory existed into it.

    Safe to run again: remembering the same file replaces it, so nothing is duplicated.
    A file that cannot be read is skipped with its reason. A memory failure (database or
    embedder offline) stops everything with DiscoveryMemoryError, because every other
    file would fail the same way; running again later picks up where it stopped.
    """

    def __init__(self, archive: DiscoveryArchive, memory: DiscoveryMemory) -> None:
        self._archive = archive
        self._memory = memory

    def execute(self) -> BackfillReport:
        remembered: list[str] = []
        skipped: list[SkippedFile] = []
        for file_name in self._archive.saved_file_names():
            try:
                discovery = self._archive.read(file_name)
            except DiscoveryStorageError as error:
                logger.warning("Skipped %s: %s", file_name, error)
                skipped.append(SkippedFile(file_name, str(error)))
                continue
            self._memory.remember(file_name, discovery)
            logger.info("Remembered %s", file_name)
            remembered.append(file_name)
        return BackfillReport(tuple(remembered), tuple(skipped))
