"""Builds her voice for the chat. Imported only when the chat runs with --voz, so the
text chat works without the voice libraries (pip install ".[voice]") installed."""

from dataclasses import dataclass

from src.application.capybara_speech import CapybaraMouth, CapybaraSpeech, SpeakerOutput
from src.infrastructure.faster_whisper_speech_recognizer import FasterWhisperSpeechRecognizer
from src.infrastructure.settings import Settings
from src.infrastructure.sounddevice_audio import SounddeviceMicrophone, SounddeviceSpeaker
from src.speech_synthesis import build_speech_synthesizer


@dataclass(frozen=True)
class CapybaraVoice:
    speech: CapybaraSpeech
    microphone: SounddeviceMicrophone


def build_capybara_voice(settings: Settings) -> CapybaraVoice:
    """Loads both models up front, so the first reply is not delayed. Raises SpeechError
    when one of them is missing."""
    synthesizer = build_speech_synthesizer(settings)
    recognizer = FasterWhisperSpeechRecognizer.load(
        settings.speech_recognition_model,
        language=settings.speech_recognition_language,
        device=settings.speech_recognition_device,
        compute_type=settings.speech_recognition_compute_type,
    )
    mouth = CapybaraMouth(synthesizer, SpeakerOutput(SounddeviceSpeaker()))
    return CapybaraVoice(CapybaraSpeech(recognizer, mouth), SounddeviceMicrophone())
