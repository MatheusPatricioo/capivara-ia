import base64
import logging

import pytest

from src.domain.speech import SpokenAudio
from src.infrastructure.websocket_voice_output import MAX_AUDIO_BYTES, WebSocketVoiceOutput
from src.infrastructure.world_messages import SpeechAudio, SpeechMessage, WorldMessage

SAMPLE_RATE = 22050
TWO_SAMPLES = b"\x01\x00\x02\x00"


class RecordingBroadcaster:
    """Keeps the broadcast messages in a list instead of sending them."""

    def __init__(self, client_count: int = 1) -> None:
        self.sent: list[tuple[WorldMessage, bool]] = []
        self._client_count = client_count

    def broadcast(self, message: WorldMessage, remember: bool = False) -> None:
        self.sent.append((message, remember))

    @property
    def client_count(self) -> int:
        return self._client_count


@pytest.fixture
def broadcaster() -> RecordingBroadcaster:
    return RecordingBroadcaster()


@pytest.fixture
def output(broadcaster: RecordingBroadcaster) -> WebSocketVoiceOutput:
    return WebSocketVoiceOutput(broadcaster)


def test_plays_audio_while_a_world_is_connected(output: WebSocketVoiceOutput) -> None:
    assert output.plays_audio


def test_does_not_play_audio_with_the_world_closed() -> None:
    output = WebSocketVoiceOutput(RecordingBroadcaster(client_count=0))

    assert not output.plays_audio


def test_a_caption_without_audio_is_sent_and_not_remembered(
    output: WebSocketVoiceOutput, broadcaster: RecordingBroadcaster
) -> None:
    output.speak("Oi, criador!", None)

    assert broadcaster.sent == [(SpeechMessage(speech_id=1, caption="Oi, criador!"), False)]


def test_her_voice_goes_with_the_caption_in_base64(
    output: WebSocketVoiceOutput, broadcaster: RecordingBroadcaster
) -> None:
    output.speak("Oi!", SpokenAudio(TWO_SAMPLES, SAMPLE_RATE))

    expected_audio = SpeechAudio(
        sample_rate=SAMPLE_RATE, pcm16_base64=base64.b64encode(TWO_SAMPLES).decode("ascii")
    )
    assert broadcaster.sent == [
        (SpeechMessage(speech_id=1, caption="Oi!", audio=expected_audio), False)
    ]


def test_silent_audio_is_left_out(
    output: WebSocketVoiceOutput, broadcaster: RecordingBroadcaster
) -> None:
    output.speak("Oi!", SpokenAudio(b"", SAMPLE_RATE))

    assert broadcaster.sent == [(SpeechMessage(speech_id=1, caption="Oi!"), False)]


def test_audio_too_long_for_one_message_goes_as_a_caption_only(
    output: WebSocketVoiceOutput,
    broadcaster: RecordingBroadcaster,
    caplog: pytest.LogCaptureFixture,
) -> None:
    too_long = SpokenAudio(bytes(MAX_AUDIO_BYTES + 2), SAMPLE_RATE)

    with caplog.at_level(logging.WARNING):
        output.speak("Uma resposta enorme.", too_long)

    assert broadcaster.sent == [(SpeechMessage(speech_id=1, caption="Uma resposta enorme."), False)]
    assert "too long to send as audio" in caplog.text


def test_each_speech_gets_a_bigger_speech_id(
    output: WebSocketVoiceOutput, broadcaster: RecordingBroadcaster
) -> None:
    output.speak("Primeira.", None)
    output.speak("Segunda.", None)

    assert broadcaster.sent == [
        (SpeechMessage(speech_id=1, caption="Primeira."), False),
        (SpeechMessage(speech_id=2, caption="Segunda."), False),
    ]
