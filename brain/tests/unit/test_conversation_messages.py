import json

import pytest
from pydantic import ValidationError

from src.domain.speech import VoiceMode
from src.infrastructure.world_messages import (
    MAX_CREATOR_MESSAGE_LENGTH,
    CreatorSaidMessage,
    ListeningMessage,
    SpeechAudio,
    SpeechMessage,
    VoiceModeMessage,
    parse_world_event,
)


def test_speech_message_without_voice_has_no_audio() -> None:
    message = SpeechMessage(speech_id=1, caption="Oi, criador!")

    assert json.loads(message.model_dump_json()) == {
        "type": "speech",
        "speech_id": 1,
        "caption": "Oi, criador!",
        "audio": None,
    }


def test_speech_message_carries_her_voice_with_its_sample_rate() -> None:
    audio = SpeechAudio(sample_rate=22050, pcm16_base64="AQACAA==")
    message = SpeechMessage(speech_id=1, caption="Oi!", audio=audio)

    assert json.loads(message.model_dump_json())["audio"] == {
        "sample_rate": 22050,
        "pcm16_base64": "AQACAA==",
    }


def test_rejects_a_speech_without_caption() -> None:
    with pytest.raises(ValidationError):
        SpeechMessage(speech_id=1, caption="")


def test_listening_message_has_the_type_and_the_seconds() -> None:
    message = ListeningMessage(seconds=120.0)

    assert json.loads(message.model_dump_json()) == {"type": "listening", "seconds": 120.0}


def test_parses_what_her_creator_said_without_surrounding_spaces() -> None:
    event = parse_world_event('{"type": "creator_said", "text": "  Oi, capivara!  "}')

    assert event == CreatorSaidMessage(text="Oi, capivara!")


def test_ignores_an_empty_message_from_her_creator() -> None:
    assert parse_world_event('{"type": "creator_said", "text": "   "}') is None


def test_ignores_a_message_from_her_creator_longer_than_the_limit() -> None:
    too_long = "a" * (MAX_CREATOR_MESSAGE_LENGTH + 1)

    assert parse_world_event(json.dumps({"type": "creator_said", "text": too_long})) is None


def test_parses_the_voice_mode_her_creator_chose() -> None:
    event = parse_world_event('{"type": "voice_mode", "mode": "mute"}')

    assert event == VoiceModeMessage(mode=VoiceMode.MUTE)


def test_ignores_an_unknown_voice_mode() -> None:
    assert parse_world_event('{"type": "voice_mode", "mode": "shout"}') is None
