"""JSON messages between the brain and the Godot world, validated by Pydantic.

Most messages go from the brain to the world (orders for the body). The world only sends
events back, like "the capybara passed close to something"; it never decides anything.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, ValidationError

from src.domain.drawing import Drawing, Stroke


class GoToMessage(BaseModel):
    type: Literal["go_to"] = "go_to"
    point: str = Field(min_length=1)


class PointMessage(BaseModel):
    x: int
    y: int


class StrokeMessage(BaseModel):
    points: list[PointMessage]


class DrawingMessage(BaseModel):
    title: str
    strokes: list[StrokeMessage]


class ChalkboardMessage(BaseModel):
    type: Literal["chalkboard"] = "chalkboard"
    drawings: list[DrawingMessage]


WorldMessage = GoToMessage | ChalkboardMessage

MAX_THING_ID_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 200

ThingId = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_THING_ID_LENGTH)
]
ThingDescription = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_DESCRIPTION_LENGTH),
]


class NoticedMessage(BaseModel):
    """Sent by the world when the capybara passes close to something worth noticing."""

    type: Literal["noticed"] = "noticed"
    thing: ThingId
    description: ThingDescription


def parse_world_event(payload: str | bytes) -> NoticedMessage | None:
    """Returns the event, or None when the payload is not a valid event from the world."""
    try:
        return NoticedMessage.model_validate_json(payload)
    except ValidationError:
        return None


def chalkboard_message(drawings: tuple[Drawing, ...]) -> ChalkboardMessage:
    return ChalkboardMessage(
        drawings=[
            DrawingMessage(
                title=drawing.title,
                strokes=[_stroke_message(stroke) for stroke in drawing.strokes],
            )
            for drawing in drawings
        ]
    )


def _stroke_message(stroke: Stroke) -> StrokeMessage:
    return StrokeMessage(points=[PointMessage(x=point.x, y=point.y) for point in stroke.points])
