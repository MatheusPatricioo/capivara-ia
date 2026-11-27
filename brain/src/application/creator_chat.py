import logging
import uuid
from collections.abc import Callable
from typing import Protocol

from opentelemetry import trace
from opentelemetry.trace import Tracer

from src.application import tracing
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

    Each answer is one trace, and all the answers of this chat share a session id, so the
    panel shows the whole conversation together.
    """

    def __init__(
        self,
        conversation: Conversation,
        presence: CreatorPresence,
        display: ConversationDisplay,
        mouth: Mouth,
        heart: Feeler | None = None,
        world_now: Callable[[], str] | None = None,
        tracer: Tracer | None = None,
    ) -> None:
        self._conversation = conversation
        self._presence = presence
        self._display = display
        self._mouth = mouth
        self._heart = heart
        self._world_now = world_now
        self._tracer = tracer or trace.get_tracer(__name__)
        self._session_id = f"creator-chat-{uuid.uuid4().hex[:12]}"

    def hear(self) -> None:
        """Called as soon as a message arrives, before it waits for its turn: her own
        thoughts pause at their next step and she stops to listen right away."""
        self._mark_exchange()

    def answer(self, message: str) -> str | None:
        """Her reply, already said; None when she could not think of one."""
        with self._tracer.start_as_current_span("creator_chat") as span:
            span.set_attribute(tracing.OBSERVATION_TYPE, tracing.AGENT)
            span.set_attribute(tracing.AGENT_NAME, tracing.CAPYBARA_AGENT_NAME)
            span.set_attribute(tracing.SESSION_ID, self._session_id)
            tracing.record_input(span, message)
            reply = self._reply_to(message, span)
            if reply is not None:
                tracing.record_output(span, reply)
            return reply

    def _reply_to(self, message: str, span: trace.Span) -> str | None:
        if self._heart is not None:
            self._heart.feel(EmotionalEvent(EventKind.TALKED_WITH_MATHEUS))
        try:
            reply = self._conversation.send(self._with_world_now(message))
        except (LanguageModelError, StepLimitReachedError) as error:
            logger.warning("She could not answer her creator: %s", error)
            tracing.mark_failed(span, str(error))
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
