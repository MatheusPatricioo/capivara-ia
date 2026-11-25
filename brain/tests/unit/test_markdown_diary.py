from datetime import date, datetime
from pathlib import Path

import pytest

from src.domain.diary import DiaryDay, DiaryEntry
from src.infrastructure.markdown_diary import DIARY_FOLDER_NAME, MarkdownDiary

AFTERNOON = DiaryEntry(datetime(2026, 11, 25, 14, 30), "Hoje pesquisei sobre vaga-lumes.")
NIGHT = DiaryEntry(datetime(2026, 11, 25, 21, 5), "Fiquei olhando as estrelas.\n\nQue noite!")
NEXT_MORNING = DiaryEntry(datetime(2026, 11, 26, 8, 0), "Acordei com chuva.")


@pytest.fixture
def diary(tmp_path: Path) -> MarkdownDiary:
    return MarkdownDiary(tmp_path)


@pytest.fixture
def diary_dir(tmp_path: Path) -> Path:
    return tmp_path / DIARY_FOLDER_NAME


def test_writes_the_entry_in_the_page_of_its_day(diary: MarkdownDiary, diary_dir: Path) -> None:
    diary.write(AFTERNOON)

    assert (diary_dir / "2026-11-25.md").read_text(encoding="utf-8") == (
        "# Diário de 25/11/2026\n\n## 14:30\n\nHoje pesquisei sobre vaga-lumes.\n"
    )


def test_a_second_entry_of_the_same_day_goes_below_the_first(
    diary: MarkdownDiary, diary_dir: Path
) -> None:
    diary.write(AFTERNOON)

    diary.write(NIGHT)

    page = (diary_dir / "2026-11-25.md").read_text(encoding="utf-8")
    assert page.endswith("## 21:05\n\nFiquei olhando as estrelas.\n\nQue noite!\n")


def test_reads_back_every_entry_of_a_day(diary: MarkdownDiary) -> None:
    diary.write(AFTERNOON)
    diary.write(NIGHT)

    assert diary.recent_days(limit=7) == [DiaryDay(date(2026, 11, 25), (AFTERNOON, NIGHT))]


def test_lists_the_newest_day_first(diary: MarkdownDiary) -> None:
    diary.write(AFTERNOON)
    diary.write(NEXT_MORNING)

    days = diary.recent_days(limit=7)

    assert [diary_day.day for diary_day in days] == [date(2026, 11, 26), date(2026, 11, 25)]


def test_lists_only_the_latest_days_up_to_the_limit(diary: MarkdownDiary) -> None:
    diary.write(AFTERNOON)
    diary.write(NEXT_MORNING)

    assert diary.recent_days(limit=1) == [DiaryDay(date(2026, 11, 26), (NEXT_MORNING,))]


def test_an_empty_diary_has_no_days(diary: MarkdownDiary) -> None:
    assert diary.recent_days(limit=7) == []


def test_ignores_files_that_are_not_diary_pages(diary: MarkdownDiary, diary_dir: Path) -> None:
    diary.write(AFTERNOON)
    (diary_dir / "rascunho.md").write_text("## 10:00\n\nnão é página", encoding="utf-8")

    assert len(diary.recent_days(limit=7)) == 1


def test_skips_a_page_with_a_broken_heading(diary: MarkdownDiary, diary_dir: Path) -> None:
    diary.write(AFTERNOON)
    (diary_dir / "2026-11-26.md").write_text("## de manhã\n\nsem hora", encoding="utf-8")

    assert diary.recent_days(limit=7) == [DiaryDay(date(2026, 11, 25), (AFTERNOON,))]
