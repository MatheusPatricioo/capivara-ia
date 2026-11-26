from src.domain.speech import SpeechError, SpokenAudio

FAKE_SAMPLE_RATE = 16000


def recording_of(text: str) -> SpokenAudio:
    """A fake recording whose bytes carry the text, so ScriptedRecognizer can read it."""
    return SpokenAudio(text.encode("utf-8"), FAKE_SAMPLE_RATE)


class ScriptedRecognizer:
    """Hears exactly the text stored in a recording made by recording_of."""

    def __init__(self) -> None:
        self.heard_recordings: list[SpokenAudio] = []

    def transcribe(self, audio: SpokenAudio) -> str:
        self.heard_recordings.append(audio)
        return audio.samples.decode("utf-8")


class BrokenRecognizer:
    def transcribe(self, audio: SpokenAudio) -> str:
        raise SpeechError("the speech model is missing")


class RecordingSynthesizer:
    """Turns text into fake audio that keeps the text, and remembers what it was asked."""

    def __init__(self) -> None:
        self.synthesized_texts: list[str] = []

    def synthesize(self, text: str) -> SpokenAudio:
        self.synthesized_texts.append(text)
        return recording_of(text)


class BrokenSynthesizer:
    def synthesize(self, text: str) -> SpokenAudio:
        raise SpeechError("the voice model is missing")


class RecordingSpeaker:
    def __init__(self) -> None:
        self.played_audios: list[SpokenAudio] = []

    def play(self, audio: SpokenAudio) -> None:
        self.played_audios.append(audio)


class RecordingVoiceOutput:
    """Keeps every caption and audio it was asked to speak."""

    def __init__(self, plays_audio: bool = True) -> None:
        self._plays_audio = plays_audio
        self.spoken: list[tuple[str, SpokenAudio | None]] = []

    @property
    def plays_audio(self) -> bool:
        return self._plays_audio

    def speak(self, caption: str, audio: SpokenAudio | None) -> None:
        self.spoken.append((caption, audio))
