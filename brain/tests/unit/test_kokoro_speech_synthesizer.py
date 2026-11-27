from pathlib import Path

import numpy as np
import pytest
from numpy.typing import NDArray

from src.domain.speech import SpeechError, SpokenAudio
from src.infrastructure.kokoro_speech_synthesizer import KokoroSpeechSynthesizer

KOKORO_SAMPLE_RATE = 24000


class RecordingEngine:
    """Answers like Kokoro: float samples in [-1, 1] and the sample rate."""

    def __init__(self) -> None:
        self.requests: list[tuple[str, str, str]] = []

    def create(
        self, text: str, voice: str, speed: float = 1.0, lang: str = "en-us"
    ) -> tuple[NDArray[np.float32], int]:
        self.requests.append((text, voice, lang))
        return np.array([0.0, 0.5, -1.0], dtype=np.float32), KOKORO_SAMPLE_RATE


class BrokenEngine:
    def create(
        self, text: str, voice: str, speed: float = 1.0, lang: str = "en-us"
    ) -> tuple[NDArray[np.float32], int]:
        raise RuntimeError("onnxruntime failed")


@pytest.fixture
def engine() -> RecordingEngine:
    return RecordingEngine()


def test_speaks_with_the_chosen_voice_and_language(engine: RecordingEngine) -> None:
    KokoroSpeechSynthesizer(engine, "pf_dora", "pt-br").synthesize("Oi, criador!")

    assert engine.requests == [("Oi, criador!", "pf_dora", "pt-br")]


def test_turns_the_float_samples_into_16_bit_audio(engine: RecordingEngine) -> None:
    spoken = KokoroSpeechSynthesizer(engine, "pf_dora", "pt-br").synthesize("Oi!")

    expected_samples = np.array([0, 16384, -32767], dtype="<i2").tobytes()
    assert spoken == SpokenAudio(expected_samples, KOKORO_SAMPLE_RATE)


def test_a_failure_of_the_engine_is_a_speech_error() -> None:
    with pytest.raises(SpeechError):
        KokoroSpeechSynthesizer(BrokenEngine(), "pf_dora", "pt-br").synthesize("Oi!")


def test_loading_without_the_model_file_says_how_to_download_it(tmp_path: Path) -> None:
    with pytest.raises(SpeechError, match="download"):
        KokoroSpeechSynthesizer.load(
            tmp_path / "kokoro-v1.0.onnx", tmp_path / "voices-v1.0.bin", "pf_dora"
        )
