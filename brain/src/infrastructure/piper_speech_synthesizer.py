from pathlib import Path

from piper import PiperVoice

from src.domain.speech import SpeechError, SpokenAudio

DOWNLOAD_HINT = (
    "download it with: python -m piper.download_voices pt_BR-faber-medium "
    "--download-dir brain/voices"
)


class PiperSpeechSynthesizer:
    """Text to speech with Piper: a small neural voice (an ONNX model) that runs on the
    CPU, offline. The model file comes with a .onnx.json beside it describing the voice."""

    def __init__(self, voice: PiperVoice) -> None:
        self._voice = voice

    @classmethod
    def load(cls, model_path: Path) -> "PiperSpeechSynthesizer":
        if not model_path.is_file():
            raise SpeechError(f"Piper voice not found at {model_path}; {DOWNLOAD_HINT}")
        return cls(PiperVoice.load(model_path))

    def synthesize(self, text: str) -> SpokenAudio:
        """Piper speaks one sentence at a time; the sentences are glued into one audio."""
        try:
            sentences = [chunk.audio_int16_bytes for chunk in self._voice.synthesize(text)]
        except RuntimeError as error:
            raise SpeechError(f"Piper could not speak: {error}") from error
        return SpokenAudio(b"".join(sentences), self._voice.config.sample_rate)
