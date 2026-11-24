import logging

from src.domain.discovery import Discovery, DiscoveryRepository
from src.domain.discovery_memory import DiscoveryMemory, DiscoveryMemoryError

logger = logging.getLogger(__name__)


class RememberingDiscoveryRepository:
    """Saves a discovery and then puts it in the long-term memory too.

    The saved file is the source of truth; the memory is an index on top of it. So a
    memory failure (database offline, embedder down) is only logged: the discovery is
    already saved, and saving it never fails because of the memory.
    """

    def __init__(self, repository: DiscoveryRepository, memory: DiscoveryMemory) -> None:
        self._repository = repository
        self._memory = memory

    def save(self, discovery: Discovery) -> str:
        file_name = self._repository.save(discovery)
        try:
            self._memory.remember(file_name, discovery)
        except DiscoveryMemoryError as error:
            logger.warning("Saved %s, but could not remember it: %s", file_name, error)
        else:
            logger.info("Remembered in the long-term memory: %s", file_name)
        return file_name
