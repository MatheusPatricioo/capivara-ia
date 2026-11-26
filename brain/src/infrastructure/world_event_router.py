import logging
from collections.abc import Callable

from src.domain.speech import VoiceMode
from src.infrastructure.world_messages import (
    CreatorSaidMessage,
    CreatorTalkingMessage,
    LetterOpenedMessage,
    LetterRepliedMessage,
    NoticedMessage,
    VoiceModeMessage,
    WorldEvent,
)

logger = logging.getLogger(__name__)


class WorldEventRouter:
    """Hands each event from the world to whoever handles that kind of event.

    The mailbox handler is registered after the world server exists, because the mailbox
    shows itself through that same server: someone has to come first.
    """

    def __init__(self, on_noticed: Callable[[NoticedMessage], None]) -> None:
        self._on_noticed = on_noticed
        self._on_letter_opened: Callable[[str], None] | None = None
        self._on_letter_replied: Callable[[str, str], None] | None = None
        self._on_creator_said: Callable[[str], None] | None = None
        self._on_voice_mode: Callable[[VoiceMode], None] | None = None
        self._on_creator_talking: Callable[[bool], None] | None = None

    def when_letter_opened(self, handler: Callable[[str], None]) -> None:
        self._on_letter_opened = handler

    def when_letter_replied(self, handler: Callable[[str, str], None]) -> None:
        """The handler gets the file name of the letter and the text of the reply."""
        self._on_letter_replied = handler

    def when_creator_said(self, handler: Callable[[str], None]) -> None:
        """The handler gets what her creator typed to her in the world."""
        self._on_creator_said = handler

    def when_voice_mode_changed(self, handler: Callable[[VoiceMode], None]) -> None:
        self._on_voice_mode = handler

    def when_creator_talking(self, handler: Callable[[bool], None]) -> None:
        """The handler gets True when he starts talking out loud and False when he stops."""
        self._on_creator_talking = handler

    def route(self, event: WorldEvent) -> None:
        match event:
            case NoticedMessage():
                self._on_noticed(event)
            case LetterOpenedMessage():
                self._letter_opened(event.letter)
            case LetterRepliedMessage():
                self._letter_replied(event.letter, event.text)
            case CreatorSaidMessage():
                self._creator_said(event.text)
            case VoiceModeMessage():
                self._voice_mode_changed(event.mode)
            case CreatorTalkingMessage():
                self._creator_talking(event.talking)

    def _letter_opened(self, file_name: str) -> None:
        if self._on_letter_opened is None:
            logger.warning("A letter was opened, but there is no mailbox: %s", file_name)
            return
        self._on_letter_opened(file_name)

    def _letter_replied(self, file_name: str, text: str) -> None:
        if self._on_letter_replied is None:
            logger.warning("A letter was answered, but there is no mailbox: %s", file_name)
            return
        self._on_letter_replied(file_name, text)

    def _creator_said(self, text: str) -> None:
        if self._on_creator_said is None:
            logger.warning("Her creator talked to her, but nobody is listening: %.80s", text)
            return
        self._on_creator_said(text)

    def _voice_mode_changed(self, mode: VoiceMode) -> None:
        if self._on_voice_mode is None:
            logger.warning("Her voice was switched to %s, but nobody uses it", mode)
            return
        self._on_voice_mode(mode)

    def _creator_talking(self, talking: bool) -> None:
        if self._on_creator_talking is None:
            logger.warning("Her creator talked out loud, but she has no ears (voice extra?)")
            return
        self._on_creator_talking(talking)
