import itertools

from src.domain.speakable_text import speakable_text
from src.infrastructure.websocket_body import MessageBroadcaster
from src.infrastructure.world_messages import ListeningMessage, SpeechMessage


class WebSocketConversationDisplay:
    """Shows the conversation with her creator in the Godot world: she stops to listen,
    and her replies appear in a speech balloon above her."""

    def __init__(self, broadcaster: MessageBroadcaster) -> None:
        self._broadcaster = broadcaster
        self._speech_ids = itertools.count(start=1)

    def show_listening(self, seconds: float) -> None:
        self._broadcaster.broadcast(ListeningMessage(seconds=seconds))

    def show_reply(self, reply: str) -> None:
        """The balloon gets the same clean text her voice will read: no markdown marks,
        emojis or web addresses, which the world's font would not show well anyway."""
        caption = speakable_text(reply)
        if not caption:
            return
        self._broadcaster.broadcast(
            SpeechMessage(speech_id=next(self._speech_ids), caption=caption)
        )
