"""When she misses Matheus, she writes him a letter and leaves it in the mailbox."""

import logging
import time
from collections.abc import Callable
from datetime import datetime
from typing import Protocol

from src.application.feelings_narrator import describe_feelings
from src.domain.body import Body, Place
from src.domain.discovery import DiscoveryCatalog
from src.domain.feelings.emotional_life import EmotionalLife
from src.domain.feelings.needs import Need
from src.domain.language_model import ChatMessage, LanguageModel, LanguageModelError, Role
from src.domain.letter import InvalidLetterError, Letter, LetterRhythm, LetterStorageError, Mailbox

logger = logging.getLogger(__name__)

MISSING_HIM_RUNG = 1
"""Rung of the bond ladder from which she writes: "missing_him", and every rung below it."""
RECENT_DISCOVERIES_TOLD = 3
FEELINGS_PLACEHOLDER = "{feelings}"
MAILBOX_PLACEHOLDER = "{mailbox}"
DISCOVERIES_PLACEHOLDER = "{discoveries}"

FIRST_LETTER = "Esta é a primeira cartinha que você escreve pra ele."
ALL_LETTERS_READ = "Ele já leu todas as cartinhas que você deixou antes."
UNREAD_LETTERS = (
    "Na caixa ainda tem {count} cartinha(s) sua(s) que ele não leu. A última dizia:\n"
    '"{last_text}"\n'
    "Não repita essa carta: conte algo novo."
)
NO_DISCOVERIES = "Você ainda não guardou nenhuma descoberta no tesouro."


class HeartCheck(Protocol):
    def check_in(self, pending_wishes: int | None = None) -> EmotionalLife: ...


class LetterWriter:
    """Runs before her cycles. Most of the time it does nothing: she only writes when she
    misses him (bond ladder) and the rhythm allows it (not too often, not too many unread).

    The model writes the letter in her voice, from her real feelings, the letters still
    waiting in the mailbox and her latest discoveries, so she has true things to tell.
    With a body, she walks to the mailbox to leave it there.
    """

    def __init__(
        self,
        heart: HeartCheck,
        mailbox: Mailbox,
        catalog: DiscoveryCatalog,
        language_model: LanguageModel,
        system_prompt: str,
        letter_prompt: str,
        rhythm: LetterRhythm,
        now: Callable[[], datetime] = datetime.now,
        clock: Callable[[], float] = time.time,
        body: Body | None = None,
    ) -> None:
        self._body = body
        self._heart = heart
        self._mailbox = mailbox
        self._catalog = catalog
        self._language_model = language_model
        self._system_prompt = system_prompt
        self._letter_prompt = letter_prompt
        self._rhythm = rhythm
        self._now = now
        self._clock = clock

    def maybe_write(self) -> str | None:
        """Returns the file name of the new letter, or None when she did not write one.

        A failure (model offline, empty letter, disk error) is only logged: she tries
        again before a later cycle.
        """
        life = self._heart.check_in()
        if life.rung_index(Need.BOND) < MISSING_HIM_RUNG:
            return None
        try:
            letters = [saved.letter for saved in self._mailbox.saved_letters()]
            written_at = self._now()
            if not self._rhythm.allows_a_new_letter(letters, written_at):
                return None
            letter = Letter(written_at, self._write(life, letters))
            if self._body is not None:
                self._body.go_to(Place.MAILBOX)
            file_name = self._mailbox.post(letter)
        except (LanguageModelError, InvalidLetterError, LetterStorageError) as error:
            logger.warning("Could not write a letter to Matheus: %s", error)
            return None
        logger.info("She wrote a letter to Matheus: %s", file_name)
        return file_name

    def _write(self, life: EmotionalLife, letters: list[Letter]) -> str:
        feelings = describe_feelings(life, self._clock())
        request = (
            self._letter_prompt.replace(FEELINGS_PLACEHOLDER, feelings)
            .replace(MAILBOX_PLACEHOLDER, _describe_mailbox(letters))
            .replace(DISCOVERIES_PLACEHOLDER, self._describe_discoveries())
        )
        reply = self._language_model.chat(
            [ChatMessage(Role.SYSTEM, self._system_prompt), ChatMessage(Role.USER, request)]
        )
        return reply.content

    def _describe_discoveries(self) -> str:
        headlines = self._catalog.latest_headlines(RECENT_DISCOVERIES_TOLD)
        if not headlines:
            return NO_DISCOVERIES
        return "\n".join(f"- {headline.title} ({headline.topic})" for headline in headlines)


def _describe_mailbox(letters: list[Letter]) -> str:
    if not letters:
        return FIRST_LETTER
    unread = [letter for letter in letters if letter.is_unread]
    if not unread:
        return ALL_LETTERS_READ
    return UNREAD_LETTERS.format(count=len(unread), last_text=unread[-1].text)
