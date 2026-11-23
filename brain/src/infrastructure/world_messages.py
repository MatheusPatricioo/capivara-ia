"""JSON messages between the brain and the Godot world, validated by Pydantic.

Most messages go from the brain to the world (orders for the body). The world only sends
events back, like "the capybara passed close to something"; it never decides anything.
"""

from typing import Annotated, Literal, assert_never

from pydantic import BaseModel, Field, StringConstraints, ValidationError

from src.domain.drawing import Circle, Drawing, Line, Rectangle, Shape, Text


class GoToMessage(BaseModel):
    type: Literal["go_to"] = "go_to"
    point: str = Field(min_length=1)


class LineMessage(BaseModel):
    type: Literal["line"] = "line"
    x1: int
    y1: int
    x2: int
    y2: int
    color: str


class CircleMessage(BaseModel):
    type: Literal["circle"] = "circle"
    x: int
    y: int
    radius: int
    color: str


class RectangleMessage(BaseModel):
    type: Literal["rectangle"] = "rectangle"
    x1: int
    y1: int
    x2: int
    y2: int
    color: str


class TextMessage(BaseModel):
    type: Literal["text"] = "text"
    x: int
    y: int
    text: str
    color: str


ShapeMessage = Annotated[
    LineMessage | CircleMessage | RectangleMessage | TextMessage, Field(discriminator="type")
]


class DrawingMessage(BaseModel):
    title: str
    shapes: list[ShapeMessage]


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
                title=drawing.title, shapes=[_shape_message(shape) for shape in drawing.shapes]
            )
            for drawing in drawings
        ]
    )


def _shape_message(shape: Shape) -> ShapeMessage:
    match shape:
        case Line(start=start, end=end, color=color):
            return LineMessage(x1=start.x, y1=start.y, x2=end.x, y2=end.y, color=color)
        case Circle(center=center, radius=radius, color=color):
            return CircleMessage(x=center.x, y=center.y, radius=radius, color=color)
        case Rectangle(top_left=top_left, bottom_right=bottom_right, color=color):
            return RectangleMessage(
                x1=top_left.x, y1=top_left.y, x2=bottom_right.x, y2=bottom_right.y, color=color
            )
        case Text(position=position, content=content, color=color):
            return TextMessage(x=position.x, y=position.y, text=content, color=color)
        case _:
            assert_never(shape)
