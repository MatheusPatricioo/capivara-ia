from typing import Any

import sounddevice

from src.domain.speech import SpeechError, SpokenAudio
from src.infrastructure.pcm_samples import PCM_DTYPE, pcm_array

MICROPHONE_SAMPLE_RATE = 16000
"""Recorded at the rate Whisper expects, so her ears never need to resample."""
MONO = 1


class SounddeviceSpeaker:
    """Plays audio on the default output device of Windows."""

    def play(self, audio: SpokenAudio) -> None:
        try:
            sounddevice.play(pcm_array(audio), audio.sample_rate, blocking=True)
        except sounddevice.PortAudioError as error:
            raise SpeechError(f"The speaker could not play: {error}") from error


class SounddeviceMicrophone:
    """Records the default input device between start_recording and stop_recording, like
    a push-to-talk button. The sound card calls _keep_block from its own thread with
    each new block of samples while the stream is open."""

    def __init__(self) -> None:
        self._blocks: list[bytes] = []
        self._stream: sounddevice.RawInputStream | None = None

    def start_recording(self) -> None:
        self._blocks = []
        try:
            self._stream = sounddevice.RawInputStream(
                samplerate=MICROPHONE_SAMPLE_RATE,
                channels=MONO,
                dtype=PCM_DTYPE,
                callback=self._keep_block,
            )
            self._stream.start()
        except sounddevice.PortAudioError as error:
            self._stream = None
            raise SpeechError(f"The microphone could not start: {error}") from error

    def stop_recording(self) -> SpokenAudio:
        """Everything recorded since start_recording (silence if it never started)."""
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        return SpokenAudio(b"".join(self._blocks), MICROPHONE_SAMPLE_RATE)

    def _keep_block(self, block: Any, frame_count: int, timing: Any, status: Any) -> None:
        self._blocks.append(bytes(block))
