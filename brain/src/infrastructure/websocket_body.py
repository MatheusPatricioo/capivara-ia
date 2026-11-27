from typing import Protocol

from src.domain.body import Place
from src.domain.feelings.emotional_life import EmotionalLife
from src.infrastructure.world_messages import (
    GoToMessage,
    WorldMessage,
    feelings_message,
)


class MessageBroadcaster(Protocol):
    def broadcast(self, message: WorldMessage, remember: bool = False) -> None: ...


class WebSocketBody:
    """Body adapter: turns body actions into messages for the Godot world."""

    def __init__(self, broadcaster: MessageBroadcaster) -> None:
        self._broadcaster = broadcaster

    def go_to(self, place: Place) -> None:
        self._broadcaster.broadcast(GoToMessage(point=place.value))

    def show_feelings(self, life: EmotionalLife) -> None:
        """Remembered, so a world opened later shows how she feels right away."""
        self._broadcaster.broadcast(feelings_message(life.emotions), remember=True)
