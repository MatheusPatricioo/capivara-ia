import logging

from src.application.voice_mode_switch import VoiceModeSwitch
from src.domain.speakable_text import speakable_text
from src.domain.speech import (
    Speaker,
    SpeechError,
    SpeechRecognizer,
    SpeechSynthesizer,
    SpokenAudio,
    VoiceMode,
    VoiceOutput,
)

logger = logging.getLogger(__name__)


class CapybaraMouth:
    """Turns the reply she wrote into what comes out of her: a clean caption and, unless
    her voice is off, the same words spoken. The output decides where: the speaker of the
    computer in the terminal chat, or her body in the world.

    Without a synthesizer (the voice libraries are not installed), she only shows captions.
    A voice failure is only logged: the caption still goes out, so the chat goes on.
    """

    def __init__(
        self,
        synthesizer: SpeechSynthesizer | None,
        output: VoiceOutput,
        voice_mode: VoiceModeSwitch | None = None,
    ) -> None:
        self._synthesizer = synthesizer
        self._output = output
        self._voice_mode = voice_mode or VoiceModeSwitch()

    def say(self, written_reply: str) -> None:
        caption = speakable_text(written_reply)
        if not caption:
            return
        self._output.speak(caption, self._voice_for(caption))

    def _voice_for(self, caption: str) -> SpokenAudio | None:
        if self._synthesizer is None or not self._wants_voice():
            return None
        try:
            return self._synthesizer.synthesize(caption)
        except SpeechError:
            logger.warning("She could not say her reply out loud", exc_info=True)
            return None

    def _wants_voice(self) -> bool:
        return self._voice_mode.mode is VoiceMode.CONVERSATION and self._output.plays_audio


class SpeakerOutput:
    """Her voice on the speaker of the computer, for the terminal chat. The caption is
    not shown here: the chat already printed the reply."""

    def __init__(self, speaker: Speaker) -> None:
        self._speaker = speaker

    @property
    def plays_audio(self) -> bool:
        return True

    def speak(self, caption: str, audio: SpokenAudio | None) -> None:
        if audio is None:
            return
        try:
            self._speaker.play(audio)
        except SpeechError:
            logger.warning("The speaker could not play her voice", exc_info=True)


class CapybaraSpeech:
    """Her ears and her mouth in the terminal chat. The chat stays the same text
    conversation: hear turns what her creator said into the text she reads, and say turns
    the reply she wrote into her voice. Typing and reading keep working beside it."""

    def __init__(self, recognizer: SpeechRecognizer, mouth: CapybaraMouth) -> None:
        self._recognizer = recognizer
        self._mouth = mouth

    def hear(self, recording: SpokenAudio) -> str:
        """What was said in the recording, or '' when nothing was. Raises SpeechError
        when the recognizer fails, so the chat can ask to repeat."""
        if recording.is_silent:
            return ""
        return self._recognizer.transcribe(recording).strip()

    def say(self, written_reply: str) -> None:
        self._mouth.say(written_reply)
