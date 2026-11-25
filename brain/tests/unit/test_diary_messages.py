from datetime import date, datetime

from src.domain.diary import DiaryDay, DiaryEntry, DiaryMood
from src.domain.feelings.emotion import Emotion
from src.infrastructure.world_messages import diary_message

HAPPY = DiaryMood(Emotion.JOY, 0.5)
TODAY = DiaryDay(
    date(2026, 11, 25),
    (
        DiaryEntry(datetime(2026, 11, 25, 14, 30), "Pesquisei sobre vaga-lumes.", HAPPY),
        DiaryEntry(datetime(2026, 11, 25, 21, 5), "Fiquei olhando as estrelas."),
    ),
)


def test_diary_message_carries_each_day_with_its_entries_and_moods_in_words() -> None:
    message = diary_message([TODAY])

    assert message.model_dump() == {
        "type": "diary",
        "days": [
            {
                "day": "2026-11-25",
                "mood": "um dia muito bom",
                "entries": [
                    {
                        "written_at": "2026-11-25T14:30",
                        "text": "Pesquisei sobre vaga-lumes.",
                        "mood": "feliz",
                    },
                    {
                        "written_at": "2026-11-25T21:05",
                        "text": "Fiquei olhando as estrelas.",
                        "mood": None,
                    },
                ],
            }
        ],
    }


def test_an_empty_diary_is_a_message_without_days() -> None:
    assert diary_message([]).days == []
