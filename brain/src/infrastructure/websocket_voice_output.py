import base64
import itertools
import logging
from typing import Protocol

from src.domain.speech import SpokenAudio
from src.infrastructure.world_messages import SpeechAudio, SpeechMessage, WorldMessage

logger = logging.getLogger(__name__)

MAX_AUDIO_BYTES = 6 * 1024 * 1024
"""Raw audio above this (about 2 minutes at 22 kHz) goes as a caption only: in base64 it
would pass the 8 MiB the world accepts in one message (inbound_buffer_size in Godot)."""


class WorldBroadcaster(Protocol):
    def broadcast(self, message: WorldMessage, remember: bool = False) -> None: ...

    @property
    def client_count(self) -> int: ...


class WebSocketVoiceOutput:
    """Her words in the Godot world: the caption goes to the balloon above her and the
    audio to a 3D sound player on her body, so her voice comes from where she is."""

    def __init__(self, broadcaster: WorldBroadcaster) -> None:
        self._broadcaster = broadcaster
        self._speech_ids = itertools.count(start=1)

    @property
    def plays_audio(self) -> bool:
        """With the world closed nobody hears her, so her voice is not even made."""
        return self._broadcaster.client_count > 0

    def speak(self, caption: str, audio: SpokenAudio | None) -> None:
        self._broadcaster.broadcast(
            SpeechMessage(
                speech_id=next(self._speech_ids),
                caption=caption,
                audio=self._speech_audio(audio),
            )
        )

    def _speech_audio(self, audio: SpokenAudio | None) -> SpeechAudio | None:
        if audio is None or audio.is_silent:
            return None
        if len(audio.samples) > MAX_AUDIO_BYTES:
            logger.warning(
                "Her reply is too long to send as audio (%.0f s); sending only the caption",
                audio.duration_seconds,
            )
            return None
        return SpeechAudio(
            sample_rate=audio.sample_rate,
            pcm16_base64=base64.b64encode(audio.samples).decode("ascii"),
        )
