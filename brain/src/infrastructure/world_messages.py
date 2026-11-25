"""JSON messages between the brain and the Godot world, validated by Pydantic.

Most messages go from the brain to the world (orders for the body). The world only sends
events back, like "the capybara passed close to something"; it never decides anything.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, ValidationError

from src.domain.drawing import Drawing, Stroke
from src.domain.feelings.emotion import EmotionalState


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


CALM_EMOTION = "calm"
"""Sent as the emotion when nothing she feels is strong enough to show."""
SHOWN_EMOTION_MIN_INTENSITY = 0.2


class FeelingsMessage(BaseModel):
    """How she feels, for the body to show it: posture, pace and a small symbol."""

    type: Literal["feelings"] = "feelings"
    emotion: str
    """Her strongest emotion, like "joy" or "loneliness", or "calm"."""
    intensity: float = Field(ge=0.0, le=1.0)
    valence: float = Field(ge=-1.0, le=1.0)
    """From -1 (all bad) to 1 (all good)."""
    arousal: float = Field(ge=0.0, le=1.0)
    """From 0 (calm, slow) to 1 (agitated)."""


WorldMessage = GoToMessage | ChalkboardMessage | FeelingsMessage

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


def feelings_message(emotions: EmotionalState) -> FeelingsMessage:
    strongest = emotions.strongest(limit=1, minimum=SHOWN_EMOTION_MIN_INTENSITY)
    emotion, intensity = strongest[0] if strongest else (CALM_EMOTION, 0.0)
    return FeelingsMessage(
        emotion=str(emotion),
        intensity=round(intensity, 3),
        valence=round(emotions.valence, 3),
        arousal=round(emotions.arousal, 3),
    )


def _stroke_message(stroke: Stroke) -> StrokeMessage:
    return StrokeMessage(points=[PointMessage(x=point.x, y=point.y) for point in stroke.points])
