import pytest

from src.domain.body import Place
from src.domain.feelings.emotion import Emotion
from src.infrastructure.websocket_body import WebSocketBody
from src.infrastructure.world_messages import (
    FeelingsMessage,
    GoToMessage,
    WorldMessage,
)
from tests.fakes.emotional_lives import a_life


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
def body(broadcaster: RecordingBroadcaster) -> WebSocketBody:
    return WebSocketBody(broadcaster)


def test_go_to_sends_the_place_id(body: WebSocketBody, broadcaster: RecordingBroadcaster) -> None:
    body.go_to(Place.COMPUTER)

    assert broadcaster.sent == [(GoToMessage(point="computer"), False)]


def test_show_feelings_sends_her_strongest_emotion_and_remembers_it(
    body: WebSocketBody, broadcaster: RecordingBroadcaster
) -> None:
    body.show_feelings(a_life({Emotion.LONELINESS: 0.6, Emotion.JOY: 0.2}))

    message, remember = broadcaster.sent[0]
    assert isinstance(message, FeelingsMessage)
    assert (message.emotion, message.intensity, remember) == ("loneliness", 0.6, True)
