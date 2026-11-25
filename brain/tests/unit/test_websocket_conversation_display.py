import pytest

from src.infrastructure.websocket_conversation_display import WebSocketConversationDisplay
from src.infrastructure.world_messages import ListeningMessage, SpeechMessage, WorldMessage


class RecordingBroadcaster:
    """Keeps the broadcast messages in a list instead of sending them."""

    def __init__(self) -> None:
        self.sent: list[tuple[WorldMessage, bool]] = []

    def broadcast(self, message: WorldMessage, remember: bool = False) -> None:
        self.sent.append((message, remember))


@pytest.fixture
def broadcaster() -> RecordingBroadcaster:
    return RecordingBroadcaster()


@pytest.fixture
def display(broadcaster: RecordingBroadcaster) -> WebSocketConversationDisplay:
    return WebSocketConversationDisplay(broadcaster)


def test_listening_is_sent_with_its_seconds_and_not_remembered(
    display: WebSocketConversationDisplay, broadcaster: RecordingBroadcaster
) -> None:
    display.show_listening(120.0)

    assert broadcaster.sent == [(ListeningMessage(seconds=120.0), False)]


def test_a_reply_becomes_a_clean_caption_that_is_not_remembered(
    display: WebSocketConversationDisplay, broadcaster: RecordingBroadcaster
) -> None:
    display.show_reply("Eu **amo** vaga-lumes! ✨")

    assert broadcaster.sent == [(SpeechMessage(speech_id=1, caption="Eu amo vaga-lumes!"), False)]


def test_each_reply_gets_a_bigger_speech_id(
    display: WebSocketConversationDisplay, broadcaster: RecordingBroadcaster
) -> None:
    display.show_reply("Primeira.")
    display.show_reply("Segunda.")

    assert broadcaster.sent == [
        (SpeechMessage(speech_id=1, caption="Primeira."), False),
        (SpeechMessage(speech_id=2, caption="Segunda."), False),
    ]


def test_a_reply_with_nothing_to_show_sends_nothing(
    display: WebSocketConversationDisplay, broadcaster: RecordingBroadcaster
) -> None:
    display.show_reply("✨🦫")

    assert broadcaster.sent == []
