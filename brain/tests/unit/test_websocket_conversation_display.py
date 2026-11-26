import pytest

from src.infrastructure.websocket_conversation_display import WebSocketConversationDisplay
from src.infrastructure.world_messages import ListeningMessage, WorldMessage


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
