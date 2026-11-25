"""Autonomous mode: the capybara lives on her own and her body follows in the Godot world."""

import logging
from collections.abc import Callable

import httpx

from src.application.attention_inbox import AttentionInbox
from src.application.autonomous_loop import AutonomousLoop
from src.application.conversation import Conversation
from src.application.feelings_voice import FeelingsVoice
from src.application.heart import Heart
from src.application.inner_voice import InnerVoice
from src.application.letter_writer import LetterWriter
from src.application.memory_query_expander import MemoryQueryExpander
from src.application.metered_language_model import MeteredLanguageModel
from src.application.related_discoveries import RelatedDiscoveries
from src.application.related_memory_chooser import RelatedMemoryChooser
from src.application.self_care import SelfCare
from src.application.shown_mailbox import ShownMailbox
from src.application.token_budget import HourlyTokenBudget
from src.capybara_heart import build_heart
from src.capybara_sky import build_world_sky, describe_sky
from src.capybara_tools import TOOL_RESULT_REMINDER_OVERRIDES, build_capybara_tools
from src.domain.attention import Attention
from src.domain.body import Body
from src.domain.discovery_memory import DiscoveryMemory
from src.domain.feelings.appraisal import EmotionalEvent, EventKind
from src.domain.feelings.behavior import cycle_pace
from src.domain.language_model import LanguageModel, StructuredLanguageModel
from src.infrastructure.logging_setup import configure_logging
from src.infrastructure.markdown_discovery_repository import MarkdownDiscoveryRepository
from src.infrastructure.markdown_mailbox import MarkdownMailbox
from src.infrastructure.markdown_suggestion_repository import MarkdownSuggestionRepository
from src.infrastructure.ollama_language_model import OllamaLanguageModel
from src.infrastructure.prompt_loader import load_prompt
from src.infrastructure.settings import Settings
from src.infrastructure.sky_broadcaster import SkyBroadcaster
from src.infrastructure.websocket_body import WebSocketBody
from src.infrastructure.websocket_mailbox_display import WebSocketMailboxDisplay
from src.infrastructure.world_event_router import WorldEventRouter
from src.infrastructure.world_messages import NoticedMessage
from src.infrastructure.world_server import WorldServer
from src.long_term_memory import open_long_term_memory

SYSTEM_PROMPT_NAME = "capybara"
TOOL_RESULT_REMINDER_NAME = "tool_result_reminder"
INNER_VOICE_NAME = "autonomous_cycle"
MEMORY_TEMPLATE_NAME = "known_discoveries"
NOTICED_TEMPLATE_NAME = "noticed_things"
RELATED_TEMPLATE_NAME = "related_discoveries"
SUGGESTIONS_TEMPLATE_NAME = "known_suggestions"
EXPAND_MEMORY_QUERY_NAME = "expand_memory_query"
CHOOSE_RELATED_MEMORY_NAME = "choose_related_memory"
FEELINGS_TEMPLATE_NAME = "feelings"
LETTER_PROMPT_NAME = "letter"
# Each message corrects the sun in the world, which moves it on its own in between.
SKY_PUBLISH_INTERVAL_SECONDS = 10.0

logger = logging.getLogger(__name__)


def print_thought(thought: str) -> None:
    print(f"Capivara (pensando): {thought}\n", flush=True)


SECONDS_PER_MINUTE = 60.0


def attention_listener(
    inbox: AttentionInbox, heart: Heart | None = None
) -> Callable[[NoticedMessage], None]:
    """Turns what the world reports into points of attention for her next cycles.

    With a heart, every new thing also sparks a little curiosity and surprise.
    """

    def notice(event: NoticedMessage) -> None:
        if inbox.notice(event.thing, event.description):
            logger.info("New point of attention: %s (%s)", event.thing, event.description)
            if heart is not None:
                heart.feel(EmotionalEvent(EventKind.NOTICED_SOMETHING))
        else:
            logger.debug("Already waiting or resting: %s", event.thing)

    return notice


def build_related_discoveries(
    settings: Settings, memory: DiscoveryMemory, language_model: StructuredLanguageModel
) -> RelatedDiscoveries:
    """The RAG pipeline of the inner voice, each step switched on in brain/.env."""
    expander = (
        MemoryQueryExpander(language_model, load_prompt(EXPAND_MEMORY_QUERY_NAME))
        if settings.memory_query_rewriting
        else None
    )
    chooser = (
        RelatedMemoryChooser(language_model, load_prompt(CHOOSE_RELATED_MEMORY_NAME))
        if settings.memory_rerank
        else None
    )
    return RelatedDiscoveries(
        memory, settings.memory_recall_min_similarity, chooser=chooser, expander=expander
    )


def build_inner_voice(
    settings: Settings,
    attention_inbox: AttentionInbox,
    related: RelatedDiscoveries,
    heart: Heart | None = None,
) -> InnerVoice:
    feelings = (
        FeelingsVoice(
            heart,
            load_prompt(FEELINGS_TEMPLATE_NAME),
            MarkdownSuggestionRepository(settings.discoveries_dir),
        )
        if heart is not None
        else None
    )
    return InnerVoice(
        invitation=load_prompt(INNER_VOICE_NAME),
        catalog=MarkdownDiscoveryRepository(settings.discoveries_dir),
        memory_template=load_prompt(MEMORY_TEMPLATE_NAME),
        max_remembered_discoveries=settings.max_remembered_discoveries,
        attention=attention_inbox,
        noticed_template=load_prompt(NOTICED_TEMPLATE_NAME),
        related=related,
        related_template=load_prompt(RELATED_TEMPLATE_NAME),
        suggestions=MarkdownSuggestionRepository(settings.discoveries_dir),
        suggestions_template=load_prompt(SUGGESTIONS_TEMPLATE_NAME),
        feelings=feelings.compose if feelings is not None else None,
    )


def _do_nothing() -> None:
    pass


def _steady_pace() -> float:
    return 1.0


def feeling_hooks(
    heart: Heart | None, body: Body
) -> tuple[Callable[[], None], Callable[[], float]]:
    """What runs before each cycle (taking care of herself) and the pace between cycles
    (slower when she is down, faster in a good tide). Without a heart, neither changes."""
    if heart is None:
        return _do_nothing, _steady_pace
    return SelfCare(heart, body).take_care, lambda: cycle_pace(heart.check_in().emotions)


def build_mailbox(
    settings: Settings,
    heart: Heart | None,
    world_server: WorldServer,
    world_events: WorldEventRouter,
) -> ShownMailbox | None:
    """The mailbox of the world, shown right away and listening for opened and answered letters.

    None without feelings (she cannot miss anyone) or with LETTERS_ENABLED off.
    """
    if heart is None or not settings.letters_enabled:
        return None
    mailbox = ShownMailbox(
        MarkdownMailbox(settings.discoveries_dir), WebSocketMailboxDisplay(world_server)
    )
    world_events.when_letter_opened(mailbox.open_letter)
    world_events.when_letter_replied(mailbox.reply_to_letter)
    mailbox.show()
    return mailbox


def build_letter_writer(
    settings: Settings,
    heart: Heart | None,
    mailbox: ShownMailbox | None,
    language_model: LanguageModel,
    system_prompt: str,
    body: Body,
) -> LetterWriter | None:
    if heart is None or mailbox is None:
        return None
    return LetterWriter(
        heart,
        mailbox,
        MarkdownDiscoveryRepository(settings.discoveries_dir),
        language_model,
        system_prompt,
        load_prompt(LETTER_PROMPT_NAME),
        settings.letter_rhythm(),
        body=body,
    )


def with_letters(
    before_cycle: Callable[[], None], letter_writer: LetterWriter | None
) -> Callable[[], None]:
    """Before each cycle: first she takes care of herself, then she may write him a letter."""
    if letter_writer is None:
        return before_cycle

    def take_care_and_write() -> None:
        before_cycle()
        letter_writer.maybe_write()

    return take_care_and_write


def main() -> None:
    settings = Settings()
    configure_logging(settings.log_file, settings.log_level)
    budget = HourlyTokenBudget(settings.max_tokens_per_hour)
    attention_inbox = AttentionInbox(
        Attention(
            settings.attention_capacity,
            rest_seconds=settings.attention_rest_minutes * SECONDS_PER_MINUTE,
        )
    )
    system_prompt = load_prompt(SYSTEM_PROMPT_NAME)
    tool_result_reminder = load_prompt(TOOL_RESULT_REMINDER_NAME)
    heart = build_heart(settings)
    world_events = WorldEventRouter(on_noticed=attention_listener(attention_inbox, heart))
    with (
        WorldServer(
            settings.world_server_host,
            settings.world_server_port,
            on_event=world_events.route,
        ) as world_server,
        httpx.Client(
            base_url=settings.ollama_base_url, timeout=settings.ollama_timeout_seconds
        ) as http_client,
        open_long_term_memory(settings, http_client) as memory,
        httpx.Client(timeout=settings.weather_timeout_seconds) as weather_client,
    ):
        body = WebSocketBody(world_server)
        if heart is not None:
            heart.watch(body.show_feelings)
            body.show_feelings(heart.check_in())
        language_model = MeteredLanguageModel(
            OllamaLanguageModel(
                client=http_client,
                model=settings.ollama_model,
                generation_options=settings.ollama_generation_options(),
            ),
            budget,
        )
        inner_voice = build_inner_voice(
            settings,
            attention_inbox,
            build_related_discoveries(settings, memory, language_model),
            heart,
        )

        def start_conversation() -> Conversation:
            return Conversation(
                language_model,
                system_prompt,
                tools=build_capybara_tools(
                    settings, language_model, http_client, body, memory, heart
                ),
                max_steps=settings.max_tool_steps,
                tool_result_reminder=tool_result_reminder,
                tool_result_reminders=TOOL_RESULT_REMINDER_OVERRIDES,
            )

        self_care, pace = feeling_hooks(heart, body)
        mailbox = build_mailbox(settings, heart, world_server, world_events)
        before_cycle = with_letters(
            self_care,
            build_letter_writer(settings, heart, mailbox, language_model, system_prompt, body),
        )
        loop = AutonomousLoop(
            start_conversation,
            budget,
            inner_voice.compose,
            settings.autonomous_cycle_interval_seconds,
            on_thought=print_thought,
            on_cycle_finished=inner_voice.release_offered,
            before_cycle=before_cycle,
            pace=pace,
        )
        print(
            f"A capivara está viva. Abra o mundo no Godot (ws://{settings.world_server_host}:"
            f"{settings.world_server_port}). Ctrl+C para encerrar.\n"
        )
        world_sky = build_world_sky(settings, weather_client)
        print(describe_sky(settings, world_sky.look()) + "\n")
        with SkyBroadcaster(world_sky, world_server, SKY_PUBLISH_INTERVAL_SECONDS):
            try:
                loop.run()
            except KeyboardInterrupt:
                print("A capivara foi dormir.")


if __name__ == "__main__":
    main()
