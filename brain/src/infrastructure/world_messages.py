"""JSON messages between the brain and the Godot world, validated by Pydantic.

Most messages go from the brain to the world (orders for the body). The world only sends
events back, like "the capybara passed close to something"; it never decides anything.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, TypeAdapter, ValidationError

from src.application.world_sky import SkyView
from src.domain.feelings.emotion import EmotionalState
from src.domain.letter import SavedLetter


class GoToMessage(BaseModel):
    type: Literal["go_to"] = "go_to"
    point: str = Field(min_length=1)


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


UNKNOWN_WEATHER = "unknown"
"""Sent as the weather while it was never read: the world keeps a clear sky."""


class SkyMessage(BaseModel):
    """The time of day and the weather, for the world to move the sun and make it rain."""

    type: Literal["sky"] = "sky"
    day_fraction: float = Field(ge=0.0, lt=1.0)
    """From 0 (midnight) to just under 1, e.g. 0.5 at noon."""
    day_length_seconds: float = Field(gt=0.0)
    """Real seconds in a world day: the world moves the sun on its own between messages."""
    weather: str
    """A sky like "clear" or "rain", or "unknown"."""


class LetterMessage(BaseModel):
    file_name: str
    """Identifies the letter when the world tells it was opened."""
    written_at: str
    """Local date and time, like "2026-11-25T14:30"."""
    text: str
    unread: bool


class MailboxMessage(BaseModel):
    """Every letter in the mailbox, the newest first. Unread ones raise its flag."""

    type: Literal["mailbox"] = "mailbox"
    letters: list[LetterMessage]


WorldMessage = GoToMessage | FeelingsMessage | SkyMessage | MailboxMessage

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


MAX_LETTER_FILE_NAME_LENGTH = 120

LetterFileName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_LETTER_FILE_NAME_LENGTH),
]


class LetterOpenedMessage(BaseModel):
    """Sent by the world when Matheus opens a letter in the mailbox."""

    type: Literal["letter_opened"] = "letter_opened"
    letter: LetterFileName


WorldEvent = NoticedMessage | LetterOpenedMessage
_WORLD_EVENT_ADAPTER: TypeAdapter[WorldEvent] = TypeAdapter(
    Annotated[WorldEvent, Field(discriminator="type")]
)


def parse_world_event(payload: str | bytes) -> WorldEvent | None:
    """Returns the event, or None when the payload is not a valid event from the world.

    The "type" field picks the model (a discriminated union), like a match on it.
    """
    try:
        return _WORLD_EVENT_ADAPTER.validate_json(payload)
    except ValidationError:
        return None


def mailbox_message(letters: list[SavedLetter]) -> MailboxMessage:
    return MailboxMessage(
        letters=[
            LetterMessage(
                file_name=saved.file_name,
                written_at=saved.letter.written_at.strftime("%Y-%m-%dT%H:%M"),
                text=saved.letter.text,
                unread=saved.letter.is_unread,
            )
            for saved in reversed(letters)
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


def sky_message(view: SkyView) -> SkyMessage:
    return SkyMessage(
        # Rounding a moment just before midnight gives 1.0: that is the next midnight, 0.0.
        day_fraction=round(view.world_time.day_fraction, 5) % 1.0,
        day_length_seconds=view.day_length_seconds,
        weather=str(view.weather.sky) if view.weather is not None else UNKNOWN_WEATHER,
    )
