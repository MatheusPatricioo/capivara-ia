from src.domain.speech import Microphone, SpeechRecognizer


class CreatorEars:
    """Her ears in the world, push to talk: the microphone records while her creator holds
    the talk button, and what he said becomes the text she reads, like a typed message.
    The brain records, so the world only says when he starts and stops talking."""

    def __init__(self, microphone: Microphone, recognizer: SpeechRecognizer) -> None:
        self._microphone = microphone
        self._recognizer = recognizer

    def start_listening(self) -> None:
        """Raises SpeechError when the microphone cannot start."""
        self._microphone.start_recording()

    def stop_listening(self) -> str:
        """What he said, or '' when nothing was. Raises SpeechError when Whisper fails."""
        recording = self._microphone.stop_recording()
        if recording.is_silent:
            return ""
        return self._recognizer.transcribe(recording).strip()
