from faster_whisper import WhisperModel

from src.domain.speech import SpeechError, SpokenAudio
from src.infrastructure.pcm_samples import float_samples

WHISPER_SAMPLE_RATE = 16000
"""Whisper was trained on 16 kHz audio and only accepts samples at that rate."""


class FasterWhisperSpeechRecognizer:
    """Speech to text with Whisper, run by faster-whisper (CTranslate2) on the machine.
    The first load downloads the model from Hugging Face; later loads read it from disk."""

    def __init__(self, model: WhisperModel, language: str) -> None:
        self._model = model
        self._language = language

    @classmethod
    def load(
        cls, model_name: str, language: str, device: str, compute_type: str
    ) -> "FasterWhisperSpeechRecognizer":
        try:
            model = WhisperModel(model_name, device=device, compute_type=compute_type)
        except (OSError, RuntimeError, ValueError) as error:
            raise SpeechError(f"Whisper model {model_name!r} could not load: {error}") from error
        return cls(model, language)

    def transcribe(self, audio: SpokenAudio) -> str:
        """The language is fixed so short phrases are not mistaken for another language.
        The VAD (voice activity detection) filter skips the silent parts, where Whisper
        would otherwise make up words."""
        samples = float_samples(audio, WHISPER_SAMPLE_RATE)
        try:
            # segments is lazy: the transcription only runs while it is read below.
            segments, _ = self._model.transcribe(samples, language=self._language, vad_filter=True)
            return " ".join(segment.text.strip() for segment in segments)
        except RuntimeError as error:
            raise SpeechError(f"Whisper could not transcribe: {error}") from error
