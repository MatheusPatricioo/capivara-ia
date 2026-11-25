from dataclasses import dataclass
from typing import Protocol

BYTES_PER_SAMPLE = 2
"""Every audio here is 16-bit PCM: two bytes per sample, one channel (mono)."""


@dataclass(frozen=True)
class SpokenAudio:
    """A piece of mono speech as raw 16-bit PCM samples (little endian), the format a WAV
    file stores. Microphones record it and synthesizers produce it."""

    samples: bytes
    sample_rate: int
    """Samples per second, in Hertz (16000 for the microphone, 22050 for the Piper voice)."""

    @property
    def is_silent(self) -> bool:
        """True when there is no sample at all, like a recording stopped right away."""
        return len(self.samples) < BYTES_PER_SAMPLE

    @property
    def duration_seconds(self) -> float:
        return len(self.samples) / BYTES_PER_SAMPLE / self.sample_rate


class SpeechError(Exception):
    """Raised when audio cannot be recorded, recognized, synthesized or played."""


class SpeechRecognizer(Protocol):
    """Speech to text (STT): her ears."""

    def transcribe(self, audio: SpokenAudio) -> str: ...


class SpeechSynthesizer(Protocol):
    """Text to speech (TTS): her mouth."""

    def synthesize(self, text: str) -> SpokenAudio: ...


class Speaker(Protocol):
    """Plays audio out loud and returns when it is over."""

    def play(self, audio: SpokenAudio) -> None: ...
