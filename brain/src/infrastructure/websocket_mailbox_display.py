from src.domain.letter import SavedLetter
from src.infrastructure.websocket_body import MessageBroadcaster
from src.infrastructure.world_messages import mailbox_message


class WebSocketMailboxDisplay:
    """Shows the mailbox in the Godot world. Remembered, so a world opened later has it."""

    def __init__(self, broadcaster: MessageBroadcaster) -> None:
        self._broadcaster = broadcaster

    def show_mailbox(self, letters: list[SavedLetter]) -> None:
        self._broadcaster.broadcast(mailbox_message(letters), remember=True)
