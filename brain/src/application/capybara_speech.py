import logging

from src.domain.speakable_text import speakable_text
from src.domain.speech import (
    Speaker,
    SpeechError,
    SpeechRecognizer,
    SpeechSynthesizer,
    SpokenAudio,
)

logger = logging.getLogger(__name__)


class CapybaraSpeech:
    """Her ears and her mouth in a chat. The chat stays the same text conversation: hear
    turns what her creator said into the text she reads, and say turns the reply she wrote
    into her voice. Typing and reading keep working beside it."""

    def __init__(
        self,
        recognizer: SpeechRecognizer,
        synthesizer: SpeechSynthesizer,
        speaker: Speaker,
    ) -> None:
        self._recognizer = recognizer
        self._synthesizer = synthesizer
        self._speaker = speaker

    def hear(self, recording: SpokenAudio) -> str:
        """What was said in the recording, or '' when nothing was. Raises SpeechError
        when the recognizer fails, so the chat can ask to repeat."""
        if recording.is_silent:
            return ""
        return self._recognizer.transcribe(recording).strip()

    def say(self, written_reply: str) -> None:
        """Says the reply out loud. A voice failure is only logged: the reply is already
        on the screen, so the chat goes on."""
        speech = speakable_text(written_reply)
        if not speech:
            return
        try:
            self._speaker.play(self._synthesizer.synthesize(speech))
        except SpeechError:
            logger.warning("She could not say her reply out loud", exc_info=True)
