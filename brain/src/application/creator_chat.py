import logging
from collections.abc import Callable
from typing import Protocol

from src.application.conversation import Conversation, StepLimitReachedError
from src.application.creator_presence import CreatorPresence
from src.application.tools.feeling_tool import Feeler
from src.domain.feelings.appraisal import EmotionalEvent, EventKind
from src.domain.language_model import LanguageModelError

logger = logging.getLogger(__name__)


class ConversationDisplay(Protocol):
    """Where the conversation shows up, like her body in the world."""

    def show_listening(self, seconds: float) -> None:
        """She stops and pays attention to her creator for the given seconds."""
        ...


class Mouth(Protocol):
    """How her reply comes out: a caption and, when her voice is on, her voice."""

    def say(self, written_reply: str) -> None: ...


class CreatorChat:
    """Her creator talking with her while she lives in the world. One conversation lasts
    the whole session, like the chat in the terminal, so she remembers what was said.

    While they talk, her own thoughts wait (CreatorPresence) and she stops to listen.
    Messages are answered one at a time, by whoever calls answer (a single worker).

    With world_now, each message reaches her with the time and weather of her world in
    front of it: the hour changes while they talk, and she should know what she is seeing.
    """

    def __init__(
        self,
        conversation: Conversation,
        presence: CreatorPresence,
        display: ConversationDisplay,
        mouth: Mouth,
        heart: Feeler | None = None,
        world_now: Callable[[], str] | None = None,
    ) -> None:
        self._conversation = conversation
        self._presence = presence
        self._display = display
        self._mouth = mouth
        self._heart = heart
        self._world_now = world_now

    def hear(self) -> None:
        """Called as soon as a message arrives, before it waits for its turn: her own
        thoughts pause at their next step and she stops to listen right away."""
        self._mark_exchange()

    def answer(self, message: str) -> str | None:
        """Her reply, already said; None when she could not think of one."""
        if self._heart is not None:
            self._heart.feel(EmotionalEvent(EventKind.TALKED_WITH_MATHEUS))
        try:
            reply = self._conversation.send(self._with_world_now(message))
        except (LanguageModelError, StepLimitReachedError) as error:
            logger.warning("She could not answer her creator: %s", error)
            return None
        if self._presence.mark_reply():
            self._display.show_listening(self._presence.quiet_seconds)
        self._mouth.say(reply)
        return reply

    def end_conversation(self) -> None:
        """He closed the chat: she goes back to her own life right away. A reply still on
        its way is said, but she no longer stops to listen."""
        self._presence.end()

    def _with_world_now(self, message: str) -> str:
        if self._world_now is None:
            return message
        return f"{self._world_now()}\n\n{message}"

    def _mark_exchange(self) -> None:
        self._presence.mark_exchange()
        self._display.show_listening(self._presence.quiet_seconds)
