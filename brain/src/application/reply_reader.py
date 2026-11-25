"""When her creator answers one of her letters, she finds the reply in the mailbox and reads it."""

import logging
from typing import Protocol

from src.domain.body import Body, Place
from src.domain.feelings.appraisal import EmotionalEvent, EventKind
from src.domain.feelings.emotional_life import EmotionalLife
from src.domain.letter import InvalidLetterError, LetterStorageError, Mailbox, SavedLetter

logger = logging.getLogger(__name__)

REPLIES_PLACEHOLDER = "{replies}"
LETTER_EXCERPT_LENGTH = 200
"""Enough of her own letter to remember what she told him; the reply comes in full."""
DATE_FORMAT = "%d/%m"


class HeartFeel(Protocol):
    def feel(self, event: EmotionalEvent) -> EmotionalLife: ...


class ReplyReader:
    """Runs around her cycles, like the attention inbox.

    Before a cycle, read_new_replies walks her to the mailbox when a reply is waiting and
    lets each new reply move her (joy, gratitude, less loneliness). During the cycle,
    compose puts the replies in her inner voice, so she thinks about them. After a cycle
    that finished, release remembers she read them, so they never come back.

    If the cycle fails, the replies are offered again next time, but each one moves her
    only once.
    """

    def __init__(
        self,
        mailbox: Mailbox,
        heart: HeartFeel,
        replies_template: str,
        body: Body | None = None,
    ) -> None:
        self._mailbox = mailbox
        self._heart = heart
        self._replies_template = replies_template
        self._body = body
        self._offered: list[SavedLetter] = []
        self._already_felt: set[str] = set()

    def read_new_replies(self) -> None:
        self._offered = self._letters_with_a_new_reply()
        if not self._offered:
            return
        if self._body is not None:
            self._body.go_to(Place.MAILBOX)
        for saved in self._offered:
            if saved.file_name not in self._already_felt:
                self._heart.feel(EmotionalEvent(EventKind.LETTER_ANSWERED))
                self._already_felt.add(saved.file_name)
                logger.info("She read her creator's reply to %s", saved.file_name)

    def compose(self) -> str:
        """The replies she found, for her inner voice; empty when there are none."""
        if not self._offered:
            return ""
        replies = "\n\n".join(self._format(saved) for saved in self._offered)
        return self._replies_template.replace(REPLIES_PLACEHOLDER, replies)

    def release(self) -> None:
        for saved in self._offered:
            try:
                self._mailbox.mark_reply_seen(saved.file_name)
            except (LetterStorageError, InvalidLetterError) as error:
                logger.warning("Could not remember she read the reply: %s", error)
                continue
            self._already_felt.discard(saved.file_name)
        self._offered = []

    def _letters_with_a_new_reply(self) -> list[SavedLetter]:
        try:
            letters = self._mailbox.saved_letters()
        except LetterStorageError as error:
            logger.warning("Could not look in the mailbox: %s", error)
            return []
        return [saved for saved in letters if saved.letter.has_a_new_reply]

    @staticmethod
    def _format(saved: SavedLetter) -> str:
        letter = saved.letter
        excerpt = letter.text[:LETTER_EXCERPT_LENGTH]
        if len(letter.text) > LETTER_EXCERPT_LENGTH:
            excerpt += "..."
        reply_text = letter.reply.text if letter.reply is not None else ""
        return (
            f'Sua cartinha de {letter.written_at.strftime(DATE_FORMAT)}: "{excerpt}"\n'
            f'A resposta dele: "{reply_text}"'
        )
