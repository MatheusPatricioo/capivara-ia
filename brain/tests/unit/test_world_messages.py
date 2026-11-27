import json

import pytest
from pydantic import ValidationError

from src.domain.feelings.emotion import Emotion, EmotionalState
from src.infrastructure.world_messages import (
    CALM_EMOTION,
    MAX_DESCRIPTION_LENGTH,
    GoToMessage,
    NoticedMessage,
    feelings_message,
    parse_world_event,
)


def test_go_to_message_has_the_type_and_the_point() -> None:
    message = GoToMessage(point="computer")

    assert json.loads(message.model_dump_json()) == {"type": "go_to", "point": "computer"}


def test_rejects_a_go_to_message_without_point() -> None:
    with pytest.raises(ValidationError):
        GoToMessage(point="")


def test_feelings_message_carries_her_strongest_emotion() -> None:
    state = EmotionalState({Emotion.JOY: 0.7, Emotion.CURIOSITY: 0.4})

    message = json.loads(feelings_message(state).model_dump_json())

    assert (message["type"], message["emotion"], message["intensity"]) == ("feelings", "joy", 0.7)


def test_feelings_message_is_calm_when_nothing_is_strong_enough() -> None:
    assert feelings_message(EmotionalState({Emotion.JOY: 0.1})).emotion == CALM_EMOTION


def test_feelings_message_tells_a_sad_state_is_negative() -> None:
    state = EmotionalState({Emotion.SADNESS: 0.8})

    assert feelings_message(state).valence < 0


def noticed_payload(**fields: object) -> str:
    event: dict[str, object] = {
        "type": "noticed",
        "thing": "water_lily",
        "description": "uma vitória-régia no lago",
    }
    event.update(fields)
    return json.dumps(event)


def test_parses_a_noticed_event_from_the_world() -> None:
    assert parse_world_event(noticed_payload()) == NoticedMessage(
        thing="water_lily", description="uma vitória-régia no lago"
    )


def test_trims_spaces_around_the_noticed_thing() -> None:
    event = parse_world_event(noticed_payload(thing="  water_lily  "))

    assert event is not None
    assert event.thing == "water_lily"


def test_ignores_a_payload_that_is_not_json() -> None:
    assert parse_world_event("the capybara saw a frog") is None


def test_ignores_an_event_of_unknown_type() -> None:
    assert parse_world_event(noticed_payload(type="smelled")) is None


def test_ignores_a_noticed_event_without_a_thing() -> None:
    assert parse_world_event(noticed_payload(thing="   ")) is None


def test_ignores_a_description_longer_than_the_limit() -> None:
    too_long_description = "a" * (MAX_DESCRIPTION_LENGTH + 1)

    assert parse_world_event(noticed_payload(description=too_long_description)) is None
