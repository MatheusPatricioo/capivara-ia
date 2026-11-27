from pathlib import Path
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

from src.domain.speech import SpeechError, SpokenAudio
from src.infrastructure.pcm_samples import pcm_audio

DOWNLOAD_HINT = (
    "download kokoro-v1.0.onnx and voices-v1.0.bin from "
    "https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.0 "
    "into brain/voices/kokoro"
)


class KokoroEngine(Protocol):
    """The part of kokoro_onnx.Kokoro this adapter uses."""

    def create(
        self, text: str, voice: str, speed: float = 1.0, lang: str = "en-us"
    ) -> tuple[NDArray[np.float32], int]: ...


class KokoroSpeechSynthesizer:
    """Text to speech with Kokoro (Apache-2.0): a small, natural voice model run with
    ONNX on the CPU, offline. pf_dora is its Brazilian Portuguese female voice."""

    def __init__(self, engine: KokoroEngine, voice: str, language: str) -> None:
        self._engine = engine
        self._voice = voice
        self._language = language

    @classmethod
    def load(
        cls, model_path: Path, voices_path: Path, voice: str, language: str = "pt-br"
    ) -> "KokoroSpeechSynthesizer":
        """kokoro_onnx is imported here, so the brain runs without the voice extra."""
        for path in (model_path, voices_path):
            if not path.is_file():
                raise SpeechError(f"Kokoro file not found at {path}; {DOWNLOAD_HINT}")
        from kokoro_onnx import Kokoro

        kokoro = Kokoro(str(model_path), str(voices_path))
        if voice not in kokoro.get_voices():
            raise SpeechError(f"Kokoro has no voice named {voice!r}")
        return cls(kokoro, voice, language)

    def synthesize(self, text: str) -> SpokenAudio:
        try:
            samples, sample_rate = self._engine.create(text, voice=self._voice, lang=self._language)
        except (RuntimeError, ValueError) as error:
            raise SpeechError(f"Kokoro could not speak: {error}") from error
        return pcm_audio(samples, sample_rate)
