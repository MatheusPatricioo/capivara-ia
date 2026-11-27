import pytest

from src.application.creator_ears import CreatorEars
from src.domain.speech import SpeechError, SpokenAudio

MICROPHONE_RATE = 16000
SPEECH = SpokenAudio(b"\x01\x00\x02\x00", MICROPHONE_RATE)
SILENCE = SpokenAudio(b"", MICROPHONE_RATE)


class FakeMicrophone:
    def __init__(self, recording: SpokenAudio) -> None:
        self.is_recording = False
        self._recording = recording

    def start_recording(self) -> None:
        self.is_recording = True

    def stop_recording(self) -> SpokenAudio:
        self.is_recording = False
        return self._recording


class FixedRecognizer:
    def __init__(self, text: str) -> None:
        self._text = text
        self.transcribed: list[SpokenAudio] = []

    def transcribe(self, audio: SpokenAudio) -> str:
        self.transcribed.append(audio)
        return self._text


class BrokenRecognizer:
    def transcribe(self, audio: SpokenAudio) -> str:
        raise SpeechError("Whisper failed")


@pytest.fixture
def microphone() -> FakeMicrophone:
    return FakeMicrophone(SPEECH)


def test_starting_to_listen_starts_the_microphone(microphone: FakeMicrophone) -> None:
    CreatorEars(microphone, FixedRecognizer("Oi")).start_listening()

    assert microphone.is_recording


def test_what_he_said_comes_back_without_surrounding_spaces(microphone: FakeMicrophone) -> None:
    ears = CreatorEars(microphone, FixedRecognizer("  Oi, capivara!  "))
    ears.start_listening()

    assert ears.stop_listening() == "Oi, capivara!"


def test_a_silent_recording_is_not_sent_to_whisper() -> None:
    recognizer = FixedRecognizer("Oi")
    ears = CreatorEars(FakeMicrophone(SILENCE), recognizer)
    ears.start_listening()
    ears.stop_listening()

    assert recognizer.transcribed == []


def test_a_silent_recording_means_nothing_was_said() -> None:
    ears = CreatorEars(FakeMicrophone(SILENCE), FixedRecognizer("Oi"))
    ears.start_listening()

    assert ears.stop_listening() == ""


def test_a_whisper_failure_is_a_speech_error(microphone: FakeMicrophone) -> None:
    ears = CreatorEars(microphone, BrokenRecognizer())
    ears.start_listening()

    with pytest.raises(SpeechError):
        ears.stop_listening()
