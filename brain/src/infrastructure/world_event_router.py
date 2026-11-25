import logging
from collections.abc import Callable

from src.infrastructure.world_messages import LetterOpenedMessage, NoticedMessage, WorldEvent

logger = logging.getLogger(__name__)


class WorldEventRouter:
    """Hands each event from the world to whoever handles that kind of event.

    The mailbox handler is registered after the world server exists, because the mailbox
    shows itself through that same server: someone has to come first.
    """

    def __init__(self, on_noticed: Callable[[NoticedMessage], None]) -> None:
        self._on_noticed = on_noticed
        self._on_letter_opened: Callable[[str], None] | None = None

    def when_letter_opened(self, handler: Callable[[str], None]) -> None:
        self._on_letter_opened = handler

    def route(self, event: WorldEvent) -> None:
        match event:
            case NoticedMessage():
                self._on_noticed(event)
            case LetterOpenedMessage():
                self._letter_opened(event.letter)

    def _letter_opened(self, file_name: str) -> None:
        if self._on_letter_opened is None:
            logger.warning("A letter was opened, but there is no mailbox: %s", file_name)
            return
        self._on_letter_opened(file_name)
