"""The mood meter of her diary, in words: how she felt in each entry and how the day went."""

from src.application.feelings_narrator import EMOTION_WORDS
from src.domain.diary import DiaryDay, DiaryMood

CALM_WORD = "tranquila"
# Average valence of the day and its word, from the best day down; the first match wins.
DAY_WORDS: tuple[tuple[float, str], ...] = (
    (0.4, "um dia muito bom"),
    (0.15, "um dia bom"),
    (-0.15, "um dia tranquilo"),
    (-0.4, "um dia difícil"),
)
WORST_DAY_WORD = "um dia muito difícil"


def entry_mood_word(mood: DiaryMood) -> str:
    """The word for one entry ("feliz", "curiosa", "sozinha"), as her inner voice says it."""
    if mood.emotion is None:
        return CALM_WORD
    return EMOTION_WORDS[mood.emotion]


def day_mood_word(diary_day: DiaryDay) -> str | None:
    """How the day went on average, or None when no entry of the day has a mood."""
    average_valence = diary_day.average_valence
    if average_valence is None:
        return None
    for lowest_valence, day_word in DAY_WORDS:
        if average_valence >= lowest_valence:
            return day_word
    return WORST_DAY_WORD
