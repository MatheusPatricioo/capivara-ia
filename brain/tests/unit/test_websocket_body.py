import pytest

from src.domain.body import Place
from src.domain.drawing import Drawing, Point, Stroke
from src.infrastructure.websocket_body import WebSocketBody
from src.infrastructure.world_messages import GoToMessage, WorldMessage, chalkboard_message

SUN_DRAWING = Drawing(title="O sol", strokes=(Stroke(points=(Point(160, 150), Point(240, 150))),))


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


def test_show_chalkboard_sends_the_drawings_and_remembers_them(
    body: WebSocketBody, broadcaster: RecordingBroadcaster
) -> None:
    body.show_chalkboard((SUN_DRAWING,))

    assert broadcaster.sent == [(chalkboard_message((SUN_DRAWING,)), True)]
