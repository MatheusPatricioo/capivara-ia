import json

import pytest
from pydantic import ValidationError

from src.domain.drawing import Drawing, Point, Stroke
from src.infrastructure.world_messages import (
    MAX_DESCRIPTION_LENGTH,
    GoToMessage,
    NoticedMessage,
    chalkboard_message,
    parse_world_event,
)

STAR_DRAWING = Drawing(
    title="Estrela",
    strokes=(Stroke(points=(Point(200, 60), Point(250, 220), Point(120, 120))),),
)


def test_go_to_message_has_the_type_and_the_point() -> None:
    message = GoToMessage(point="computer")

    assert json.loads(message.model_dump_json()) == {"type": "go_to", "point": "computer"}


def test_rejects_a_go_to_message_without_point() -> None:
    with pytest.raises(ValidationError):
        GoToMessage(point="")


def test_chalkboard_message_lists_every_stroke_with_its_points() -> None:
    message = chalkboard_message((STAR_DRAWING,))

    assert json.loads(message.model_dump_json()) == {
        "type": "chalkboard",
        "drawings": [
            {
                "title": "Estrela",
                "strokes": [
                    {"points": [{"x": 200, "y": 60}, {"x": 250, "y": 220}, {"x": 120, "y": 120}]},
                ],
            }
        ],
    }


def test_empty_chalkboard_message_has_no_drawings() -> None:
    assert chalkboard_message(()).drawings == []


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
