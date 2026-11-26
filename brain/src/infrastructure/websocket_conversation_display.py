from src.infrastructure.websocket_body import MessageBroadcaster
from src.infrastructure.world_messages import ListeningMessage


class WebSocketConversationDisplay:
    """Shows in the Godot world that she is listening to her creator: she stops and faces
    the camera. Her replies go out through her mouth (WebSocketVoiceOutput)."""

    def __init__(self, broadcaster: MessageBroadcaster) -> None:
        self._broadcaster = broadcaster

    def show_listening(self, seconds: float) -> None:
        self._broadcaster.broadcast(ListeningMessage(seconds=seconds))
