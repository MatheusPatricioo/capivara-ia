import threading

from src.domain.speech import VoiceMode


class VoiceModeSwitch:
    """The voice mode her creator chose in the world. The world server thread changes it
    and the thread that answers him reads it, so a lock keeps them in step."""

    def __init__(self, mode: VoiceMode = VoiceMode.CONVERSATION) -> None:
        self._mode = mode
        self._lock = threading.Lock()

    @property
    def mode(self) -> VoiceMode:
        with self._lock:
            return self._mode

    def switch_to(self, mode: VoiceMode) -> None:
        with self._lock:
            self._mode = mode
