from src.domain.diary import DiaryDay
from src.infrastructure.websocket_body import MessageBroadcaster
from src.infrastructure.world_messages import diary_message


class WebSocketDiaryDisplay:
    """Shows her diary in the Godot world. Remembered, so a world opened later has it."""

    def __init__(self, broadcaster: MessageBroadcaster) -> None:
        self._broadcaster = broadcaster

    def show_diary(self, days: list[DiaryDay]) -> None:
        self._broadcaster.broadcast(diary_message(days), remember=True)
