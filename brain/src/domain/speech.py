from dataclasses import dataclass
from enum import StrEnum
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


class Microphone(Protocol):
    """Records between start_recording and stop_recording, like a push-to-talk button."""

    def start_recording(self) -> None: ...

    def stop_recording(self) -> SpokenAudio: ...


SEMITONES_PER_OCTAVE = 12


@dataclass(frozen=True)
class VoiceEffect:
    """A change applied to her voice after any synthesizer made it, set in the .env."""

    pitch_semitones: float = 0.0
    """How much higher (or lower, when negative) she sounds; 12 semitones is an octave."""
    speed: float = 1.0
    """How fast she talks: 1.1 is 10% faster, whatever the pitch."""

    @property
    def is_neutral(self) -> bool:
        return self.pitch_semitones == 0.0 and self.speed == 1.0

    @property
    def pitch_ratio(self) -> float:
        """How many times higher every frequency gets: 2.0 for +12 semitones."""
        return float(2 ** (self.pitch_semitones / SEMITONES_PER_OCTAVE))


class VoiceMode(StrEnum):
    """How much she speaks out loud, chosen by her creator."""

    MUTE = "mute"
    """Only the caption, no voice."""
    CONVERSATION = "conversation"
    """She says her replies to her creator out loud."""


class VoiceOutput(Protocol):
    """Where her words come out: a caption to read and, when there is one, her voice."""

    @property
    def plays_audio(self) -> bool:
        """False when nobody would hear it, so the voice is not even synthesized."""
        ...

    def speak(self, caption: str, audio: SpokenAudio | None) -> None: ...
