"""JSON messages between the brain and the Godot world, validated by Pydantic.

Most messages go from the brain to the world (orders for the body). The world only sends
events back, like "the capybara passed close to something"; it never decides anything.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, TypeAdapter, ValidationError

from src.application.diary_mood_words import day_mood_word, entry_mood_word
from src.application.world_sky import SkyView
from src.domain.diary import DiaryDay, DiaryEntry
from src.domain.feelings.emotion import EmotionalState
from src.domain.letter import MAX_LETTER_LENGTH, Reply, SavedLetter
from src.domain.speech import VoiceMode

WORLD_DATE_FORMAT = "%Y-%m-%dT%H:%M"


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
    replied_at: str | None = None
    """When her creator answered, like "written_at"; None while unanswered."""
    reply: str | None = None


class MailboxMessage(BaseModel):
    """Every letter in the mailbox, the newest first. Unread ones raise its flag."""

    type: Literal["mailbox"] = "mailbox"
    letters: list[LetterMessage]


class DiaryEntryMessage(BaseModel):
    written_at: str
    """Local date and time, like "2026-11-25T14:30"."""
    text: str
    mood: str | None = None
    """How she felt, in one word ("feliz", "tranquila"); None for entries without a mood."""


class DiaryDayMessage(BaseModel):
    day: str
    """Like "2026-11-25"."""
    entries: list[DiaryEntryMessage]
    """The earliest first, as she wrote them."""
    mood: str | None = None
    """How the day went ("um dia bom"); None when no entry of the day has a mood."""


class DiaryMessage(BaseModel):
    """The latest pages of her diary, the newest day first."""

    type: Literal["diary"] = "diary"
    days: list[DiaryDayMessage]


class ListeningMessage(BaseModel):
    """She stops, faces her creator and listens for the given seconds. Sent again on every
    exchange, so the world only extends the time and never needs an "it is over" message."""

    type: Literal["listening"] = "listening"
    seconds: float = Field(gt=0.0)


class SpeechAudio(BaseModel):
    """Her voice: 16-bit mono PCM, little endian, in base64, because JSON only carries text.
    The world plays it from these bytes, without writing a file."""

    sample_rate: int = Field(gt=0)
    pcm16_base64: str = Field(min_length=1)


class SpeechMessage(BaseModel):
    """Something she says, shown in a speech balloon above her and, when there is audio,
    said by her voice. Never remembered: a world that connects later must not hear old
    replies."""

    type: Literal["speech"] = "speech"
    speech_id: int = Field(ge=1)
    """Grows with every speech: the world drops one older than the speech it is showing,
    and a new one interrupts the one still playing."""
    caption: str = Field(min_length=1)
    audio: SpeechAudio | None = None
    """None when her voice is off (Mute) or could not be made: then only the caption."""


class HeardMessage(BaseModel):
    """What she understood when her creator talked to her out loud ("" when nothing),
    so the world can show it. Never remembered."""

    type: Literal["heard"] = "heard"
    text: str


WorldMessage = (
    GoToMessage
    | FeelingsMessage
    | SkyMessage
    | MailboxMessage
    | DiaryMessage
    | ListeningMessage
    | SpeechMessage
    | HeardMessage
)

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
    """Sent by the world when her creator opens a letter in the mailbox."""

    type: Literal["letter_opened"] = "letter_opened"
    letter: LetterFileName


ReplyText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_LETTER_LENGTH),
]


class LetterRepliedMessage(BaseModel):
    """Sent by the world when her creator writes back to a letter."""

    type: Literal["letter_replied"] = "letter_replied"
    letter: LetterFileName
    text: ReplyText


MAX_CREATOR_MESSAGE_LENGTH = 2000

CreatorMessageText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_CREATOR_MESSAGE_LENGTH),
]


class CreatorSaidMessage(BaseModel):
    """Sent by the world when her creator talks to her (typed in the chat box)."""

    type: Literal["creator_said"] = "creator_said"
    text: CreatorMessageText


class VoiceModeMessage(BaseModel):
    """Sent by the world when it connects and whenever her creator switches her voice."""

    type: Literal["voice_mode"] = "voice_mode"
    mode: VoiceMode


class CreatorTalkingMessage(BaseModel):
    """Sent by the world when her creator presses (true) and releases (false) the talk
    button: the brain records the microphone in between."""

    type: Literal["creator_talking"] = "creator_talking"
    talking: bool


WorldEvent = (
    NoticedMessage
    | LetterOpenedMessage
    | LetterRepliedMessage
    | CreatorSaidMessage
    | VoiceModeMessage
    | CreatorTalkingMessage
)
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
                written_at=saved.letter.written_at.strftime(WORLD_DATE_FORMAT),
                text=saved.letter.text,
                unread=saved.letter.is_unread,
                replied_at=_replied_at(saved.letter.reply),
                reply=saved.letter.reply.text if saved.letter.reply else None,
            )
            for saved in reversed(letters)
        ]
    )


def diary_message(days: list[DiaryDay]) -> DiaryMessage:
    return DiaryMessage(
        days=[
            DiaryDayMessage(
                day=diary_day.day.isoformat(),
                entries=[_diary_entry_message(entry) for entry in diary_day.entries],
                mood=day_mood_word(diary_day),
            )
            for diary_day in days
        ]
    )


def _diary_entry_message(entry: DiaryEntry) -> DiaryEntryMessage:
    return DiaryEntryMessage(
        written_at=entry.written_at.strftime(WORLD_DATE_FORMAT),
        text=entry.text,
        mood=entry_mood_word(entry.mood) if entry.mood is not None else None,
    )


def _replied_at(reply: Reply | None) -> str | None:
    return reply.written_at.strftime(WORLD_DATE_FORMAT) if reply else None


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
