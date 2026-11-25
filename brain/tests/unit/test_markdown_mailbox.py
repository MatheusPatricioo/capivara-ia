from datetime import datetime
from pathlib import Path

import pytest

from src.domain.letter import (
    InvalidLetterError,
    Letter,
    LetterStatus,
    LetterStorageError,
    Reply,
    SavedLetter,
)
from src.infrastructure.markdown_mailbox import LETTERS_FOLDER_NAME, MarkdownMailbox

WRITTEN_AT = datetime(2026, 11, 25, 14, 30)
LETTER = Letter(WRITTEN_AT, "Oi, criador!\n\nSenti sua falta.\nCapivara")
FILE_NAME = "2026-11-25-carta-para-o-criador.md"


@pytest.fixture
def mailbox(tmp_path: Path) -> MarkdownMailbox:
    return MarkdownMailbox(tmp_path)


def test_saves_the_letter_in_the_letters_folder(mailbox: MarkdownMailbox, tmp_path: Path) -> None:
    file_name = mailbox.post(LETTER)

    assert (tmp_path / LETTERS_FOLDER_NAME / file_name).is_file()


def test_names_the_file_with_the_date(mailbox: MarkdownMailbox) -> None:
    assert mailbox.post(LETTER) == FILE_NAME


def test_two_letters_on_the_same_day_get_different_files(mailbox: MarkdownMailbox) -> None:
    mailbox.post(LETTER)

    assert mailbox.post(LETTER) == "2026-11-25-carta-para-o-criador-2.md"


def test_reads_back_the_letter_it_saved(mailbox: MarkdownMailbox) -> None:
    mailbox.post(LETTER)

    assert mailbox.saved_letters() == [SavedLetter(FILE_NAME, LETTER)]


def test_has_no_letters_before_the_first_one(mailbox: MarkdownMailbox) -> None:
    assert mailbox.saved_letters() == []


def test_lists_the_letters_from_the_oldest(mailbox: MarkdownMailbox) -> None:
    newer = Letter(datetime(2026, 11, 26, 9, 0), "Bom dia!")
    mailbox.post(newer)
    mailbox.post(LETTER)

    assert [saved.letter for saved in mailbox.saved_letters()] == [LETTER, newer]


def test_a_letter_marked_as_read_by_hand_is_read(mailbox: MarkdownMailbox, tmp_path: Path) -> None:
    letter_file = tmp_path / LETTERS_FOLDER_NAME / mailbox.post(LETTER)
    letter_file.write_text(
        letter_file.read_text(encoding="utf-8").replace("não lida", "lida"), encoding="utf-8"
    )

    assert mailbox.saved_letters()[0].letter.status is LetterStatus.READ


def test_skips_a_file_that_is_not_a_letter(mailbox: MarkdownMailbox, tmp_path: Path) -> None:
    mailbox.post(LETTER)
    (tmp_path / LETTERS_FOLDER_NAME / "anotacao.md").write_text("uma nota", encoding="utf-8")

    assert mailbox.saved_letters() == [SavedLetter(FILE_NAME, LETTER)]


def test_mark_read_saves_the_letter_as_read(mailbox: MarkdownMailbox) -> None:
    mailbox.mark_read(mailbox.post(LETTER))

    assert mailbox.saved_letters()[0].letter.status is LetterStatus.READ


def test_mark_read_fails_for_a_letter_that_does_not_exist(mailbox: MarkdownMailbox) -> None:
    with pytest.raises(LetterStorageError):
        mailbox.mark_read("2026-01-01-carta-que-nao-existe.md")


def test_mark_read_refuses_a_file_outside_the_letters_folder(mailbox: MarkdownMailbox) -> None:
    with pytest.raises(LetterStorageError):
        mailbox.mark_read("../segredo.md")


def test_keeps_the_reply_with_the_letter(mailbox: MarkdownMailbox) -> None:
    reply = Reply(datetime(2026, 11, 26, 10, 0), "Oi, capivara!\n\nVolto amanhã.")

    mailbox.answer(mailbox.post(LETTER), reply)

    assert mailbox.saved_letters()[0].letter.reply == reply


def test_writes_the_reply_under_its_own_heading(mailbox: MarkdownMailbox, tmp_path: Path) -> None:
    file_name = mailbox.post(LETTER)

    mailbox.answer(file_name, Reply(datetime(2026, 11, 26, 10, 0), "Volto amanhã."))

    letter_text = (tmp_path / LETTERS_FOLDER_NAME / file_name).read_text(encoding="utf-8")
    assert letter_text.endswith("## Resposta do criador\n\nVolto amanhã.\n")


def test_refuses_a_second_reply(mailbox: MarkdownMailbox) -> None:
    file_name = mailbox.post(LETTER)
    mailbox.answer(file_name, Reply(datetime(2026, 11, 26, 10, 0), "Volto amanhã."))

    with pytest.raises(InvalidLetterError):
        mailbox.answer(file_name, Reply(datetime(2026, 11, 26, 11, 0), "Mudei de ideia."))


def test_a_new_reply_is_saved_as_not_seen_by_her(mailbox: MarkdownMailbox) -> None:
    mailbox.answer(mailbox.post(LETTER), Reply(datetime(2026, 11, 26, 10, 0), "Volto amanhã."))

    assert mailbox.saved_letters()[0].letter.has_a_new_reply


def test_remembers_she_read_the_reply(mailbox: MarkdownMailbox) -> None:
    file_name = mailbox.post(LETTER)
    mailbox.answer(file_name, Reply(datetime(2026, 11, 26, 10, 0), "Volto amanhã."))

    mailbox.mark_reply_seen(file_name)

    assert not mailbox.saved_letters()[0].letter.has_a_new_reply
