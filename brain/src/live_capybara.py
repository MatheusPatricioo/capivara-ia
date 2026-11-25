"""Autonomous mode: the capybara lives on her own and her body follows in the Godot world."""

import logging
from collections.abc import Callable

import httpx

from src.application.attention_inbox import AttentionInbox
from src.application.autonomous_loop import AutonomousLoop
from src.application.conversation import Conversation
from src.application.diary_keeper import DiaryKeeper
from src.application.feelings_voice import FeelingsVoice
from src.application.heart import Heart
from src.application.inner_voice import InnerVoice
from src.application.memory_query_expander import MemoryQueryExpander
from src.application.metered_language_model import MeteredLanguageModel
from src.application.related_discoveries import RelatedDiscoveries
from src.application.related_memory_chooser import RelatedMemoryChooser
from src.application.self_care import SelfCare
from src.application.token_budget import HourlyTokenBudget
from src.capybara_chat import (
    build_world_creator_chat,
    creator_presence,
    listen_to_creator,
    start_creator_conversation,
)
from src.capybara_diary import build_diary_keeper
from src.capybara_heart import build_heart
from src.capybara_letters import CapybaraLetters, build_letters
from src.capybara_sky import build_world_sky, describe_sky
from src.capybara_tools import TOOL_RESULT_REMINDER_OVERRIDES, build_capybara_tools
from src.domain.attention import Attention
from src.domain.body import Body
from src.domain.discovery_memory import DiscoveryMemory
from src.domain.feelings.appraisal import EmotionalEvent, EventKind
from src.domain.feelings.behavior import cycle_pace
from src.domain.language_model import StructuredLanguageModel
from src.infrastructure.logging_setup import configure_logging
from src.infrastructure.markdown_discovery_repository import MarkdownDiscoveryRepository
from src.infrastructure.markdown_suggestion_repository import MarkdownSuggestionRepository
from src.infrastructure.ollama_language_model import OllamaLanguageModel
from src.infrastructure.prompt_loader import load_prompt
from src.infrastructure.serial_worker import SerialWorker
from src.infrastructure.settings import Settings
from src.infrastructure.sky_broadcaster import SkyBroadcaster
from src.infrastructure.websocket_body import WebSocketBody
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
# Each message corrects the sun in the world, which moves it on its own in between.
SKY_PUBLISH_INTERVAL_SECONDS = 10.0
SECONDS_PER_MINUTE = 60.0

logger = logging.getLogger(__name__)


def print_thought(thought: str) -> None:
    print(f"Capivara (pensando): {thought}\n", flush=True)


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


def build_attention_inbox(settings: Settings) -> AttentionInbox:
    return AttentionInbox(
        Attention(
            settings.attention_capacity,
            rest_seconds=settings.attention_rest_minutes * SECONDS_PER_MINUTE,
        )
    )


def build_language_model(
    settings: Settings, http_client: httpx.Client, budget: HourlyTokenBudget
) -> MeteredLanguageModel:
    """The local model, with every call counted against the hourly token budget."""
    return MeteredLanguageModel(
        OllamaLanguageModel(
            client=http_client,
            model=settings.ollama_model,
            generation_options=settings.ollama_generation_options(),
        ),
        budget,
    )


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
    replies: Callable[[], str] | None = None,
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
        replies=replies,
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


def before_each_cycle(
    self_care: Callable[[], None], letters: CapybaraLetters | None
) -> Callable[[], None]:
    """First she takes care of herself, then she reads his replies and may write to him."""
    if letters is None:
        return self_care

    def take_care_then_write() -> None:
        self_care()
        letters.before_cycle()

    return take_care_then_write


def after_each_cycle(
    inner_voice: InnerVoice, letters: CapybaraLetters | None
) -> Callable[[], None]:
    """After a cycle that finished: she lets go of what she noticed and of the replies she read."""
    if letters is None:
        return inner_voice.release_offered

    def release_everything() -> None:
        inner_voice.release_offered()
        letters.after_cycle()

    return release_everything


def think_aloud_and_write(diary_keeper: DiaryKeeper) -> Callable[[str], None]:
    """Each thought of a cycle is printed in the terminal and kept in her diary."""

    def print_and_keep(thought: str) -> None:
        print_thought(thought)
        diary_keeper.keep(thought)

    return print_and_keep


def main() -> None:
    settings = Settings()
    configure_logging(settings.log_file, settings.log_level)
    budget = HourlyTokenBudget(settings.max_tokens_per_hour)
    attention_inbox = build_attention_inbox(settings)
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
        language_model = build_language_model(settings, http_client, budget)
        letters = build_letters(
            settings, heart, world_server, world_events, language_model, system_prompt, body
        )
        inner_voice = build_inner_voice(
            settings,
            attention_inbox,
            build_related_discoveries(settings, memory, language_model),
            heart,
            replies=letters.reply_reader.compose if letters is not None else None,
        )

        presence = creator_presence(settings)
        creator_chat = build_world_creator_chat(
            start_creator_conversation(settings, language_model, http_client, memory, heart),
            presence,
            world_server,
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
                before_step=presence.wait_while_talking,
            )

        self_care, pace = feeling_hooks(heart, body)
        loop = AutonomousLoop(
            start_conversation,
            budget,
            inner_voice.compose,
            settings.autonomous_cycle_interval_seconds,
            on_thought=think_aloud_and_write(build_diary_keeper(settings, world_server, heart)),
            on_cycle_finished=after_each_cycle(inner_voice, letters),
            before_cycle=before_each_cycle(self_care, letters),
            pace=pace,
            wait_for_turn=presence.wait_while_talking,
        )
        print(
            f"A capivara está viva. Abra o mundo no Godot (ws://{settings.world_server_host}:"
            f"{settings.world_server_port}). Ctrl+C para encerrar.\n"
        )
        world_sky = build_world_sky(settings, weather_client)
        print(describe_sky(settings, world_sky.look()) + "\n")
        with (
            SkyBroadcaster(world_sky, world_server, SKY_PUBLISH_INTERVAL_SECONDS),
            SerialWorker("creator-chat") as chat_worker,
        ):
            world_events.when_creator_said(listen_to_creator(creator_chat, chat_worker))
            try:
                loop.run()
            except KeyboardInterrupt:
                print("A capivara foi dormir.")


if __name__ == "__main__":
    main()
