import json

import pytest
from pydantic import ValidationError

from src.infrastructure.world_messages import (
    MAX_CREATOR_MESSAGE_LENGTH,
    CreatorSaidMessage,
    ListeningMessage,
    SpeechMessage,
    parse_world_event,
)


def test_speech_message_has_the_type_the_id_and_the_caption() -> None:
    message = SpeechMessage(speech_id=1, caption="Oi, criador!")

    assert json.loads(message.model_dump_json()) == {
        "type": "speech",
        "speech_id": 1,
        "caption": "Oi, criador!",
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
