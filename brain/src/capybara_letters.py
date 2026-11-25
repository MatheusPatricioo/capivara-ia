"""Builds her letters: the mailbox in the world, the letters she writes and the replies to them."""

from dataclasses import dataclass

from src.application.heart import Heart
from src.application.letter_writer import LetterWriter
from src.application.reply_reader import ReplyReader
from src.application.shown_mailbox import ShownMailbox
from src.domain.body import Body
from src.domain.language_model import LanguageModel
from src.infrastructure.markdown_discovery_repository import MarkdownDiscoveryRepository
from src.infrastructure.markdown_mailbox import MarkdownMailbox
from src.infrastructure.prompt_loader import load_prompt
from src.infrastructure.settings import Settings
from src.infrastructure.websocket_mailbox_display import WebSocketMailboxDisplay
from src.infrastructure.world_event_router import WorldEventRouter
from src.infrastructure.world_server import WorldServer

LETTER_PROMPT_NAME = "letter"
LETTER_REPLIES_TEMPLATE_NAME = "letter_replies"


@dataclass(frozen=True)
class CapybaraLetters:
    """Everything about her letters, run around each cycle of the live capybara."""

    writer: LetterWriter
    reply_reader: ReplyReader

    def before_cycle(self) -> None:
        """She reads his replies first: a reply that made her happy can spare a letter."""
        self.reply_reader.read_new_replies()
        self.writer.maybe_write()

    def after_cycle(self) -> None:
        """After a cycle that finished, the replies she read never come back."""
        self.reply_reader.release()


def build_letters(
    settings: Settings,
    heart: Heart | None,
    world: WorldServer,
    world_events: WorldEventRouter,
    language_model: LanguageModel,
    system_prompt: str,
    body: Body,
) -> CapybaraLetters | None:
    """None without feelings (she cannot miss anyone) or with LETTERS_ENABLED off."""
    if heart is None or not settings.letters_enabled:
        return None
    mailbox = _build_mailbox(settings, world, world_events)
    writer = LetterWriter(
        heart,
        mailbox,
        MarkdownDiscoveryRepository(settings.discoveries_dir),
        language_model,
        system_prompt,
        load_prompt(LETTER_PROMPT_NAME),
        settings.letter_rhythm(),
        body=body,
    )
    reply_reader = ReplyReader(mailbox, heart, load_prompt(LETTER_REPLIES_TEMPLATE_NAME), body=body)
    return CapybaraLetters(writer, reply_reader)


def _build_mailbox(
    settings: Settings, world: WorldServer, world_events: WorldEventRouter
) -> ShownMailbox:
    """The mailbox of the world, shown right away and listening for opened and answered letters."""
    mailbox = ShownMailbox(
        MarkdownMailbox(settings.discoveries_dir), WebSocketMailboxDisplay(world)
    )
    world_events.when_letter_opened(mailbox.open_letter)
    world_events.when_letter_replied(mailbox.reply_to_letter)
    mailbox.show()
    return mailbox
