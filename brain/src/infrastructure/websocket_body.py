from typing import Protocol

from src.domain.body import Place
from src.domain.drawing import Drawing
from src.infrastructure.world_messages import GoToMessage, WorldMessage, chalkboard_message


class MessageBroadcaster(Protocol):
    def broadcast(self, message: WorldMessage, remember: bool = False) -> None: ...


class WebSocketBody:
    """Body adapter: turns body actions into messages for the Godot world."""

    def __init__(self, broadcaster: MessageBroadcaster) -> None:
        self._broadcaster = broadcaster

    def go_to(self, place: Place) -> None:
        self._broadcaster.broadcast(GoToMessage(point=place.value))

    def show_chalkboard(self, drawings: tuple[Drawing, ...]) -> None:
        self._broadcaster.broadcast(chalkboard_message(drawings), remember=True)
