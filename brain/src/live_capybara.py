"""Autonomous mode: the capybara lives on her own and her body follows in the Godot world."""

import logging
from collections.abc import Callable

import httpx

from src.application.attention_inbox import AttentionInbox
from src.application.autonomous_loop import AutonomousLoop
from src.application.conversation import Conversation
from src.application.inner_voice import InnerVoice
from src.application.metered_language_model import MeteredLanguageModel
from src.application.related_discoveries import RelatedDiscoveries
from src.application.token_budget import HourlyTokenBudget
from src.capybara_tools import TOOL_RESULT_REMINDER_OVERRIDES, build_capybara_tools
from src.domain.attention import Attention
from src.domain.chalkboard import Chalkboard
from src.domain.discovery_memory import DiscoveryMemory
from src.infrastructure.logging_setup import configure_logging
from src.infrastructure.markdown_discovery_repository import MarkdownDiscoveryRepository
from src.infrastructure.markdown_suggestion_repository import MarkdownSuggestionRepository
from src.infrastructure.ollama_language_model import OllamaLanguageModel
from src.infrastructure.prompt_loader import load_prompt
from src.infrastructure.settings import Settings
from src.infrastructure.websocket_body import WebSocketBody
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

logger = logging.getLogger(__name__)


def print_thought(thought: str) -> None:
    print(f"Capivara (pensando): {thought}\n", flush=True)


SECONDS_PER_MINUTE = 60.0


def attention_listener(inbox: AttentionInbox) -> Callable[[NoticedMessage], None]:
    """Turns what the world reports into points of attention for her next cycles."""

    def notice(event: NoticedMessage) -> None:
        if inbox.notice(event.thing, event.description):
            logger.info("New point of attention: %s (%s)", event.thing, event.description)
        else:
            logger.debug("Already waiting or resting: %s", event.thing)

    return notice


def build_inner_voice(
    settings: Settings, attention_inbox: AttentionInbox, memory: DiscoveryMemory
) -> InnerVoice:
    return InnerVoice(
        invitation=load_prompt(INNER_VOICE_NAME),
        catalog=MarkdownDiscoveryRepository(settings.discoveries_dir),
        memory_template=load_prompt(MEMORY_TEMPLATE_NAME),
        max_remembered_discoveries=settings.max_remembered_discoveries,
        attention=attention_inbox,
        noticed_template=load_prompt(NOTICED_TEMPLATE_NAME),
        related=RelatedDiscoveries(memory, settings.memory_recall_min_similarity),
        related_template=load_prompt(RELATED_TEMPLATE_NAME),
        suggestions=MarkdownSuggestionRepository(settings.discoveries_dir),
        suggestions_template=load_prompt(SUGGESTIONS_TEMPLATE_NAME),
    )


def main() -> None:
    settings = Settings()
    configure_logging(settings.log_file, settings.log_level)
    budget = HourlyTokenBudget(settings.max_tokens_per_hour)
    chalkboard = Chalkboard(settings.chalkboard_capacity)
    attention_inbox = AttentionInbox(
        Attention(
            settings.attention_capacity,
            rest_seconds=settings.attention_rest_minutes * SECONDS_PER_MINUTE,
        )
    )
    system_prompt = load_prompt(SYSTEM_PROMPT_NAME)
    tool_result_reminder = load_prompt(TOOL_RESULT_REMINDER_NAME)
    with (
        WorldServer(
            settings.world_server_host,
            settings.world_server_port,
            on_event=attention_listener(attention_inbox),
        ) as world_server,
        httpx.Client(
            base_url=settings.ollama_base_url, timeout=settings.ollama_timeout_seconds
        ) as http_client,
        open_long_term_memory(settings, http_client) as memory,
    ):
        inner_voice = build_inner_voice(settings, attention_inbox, memory)
        body = WebSocketBody(world_server)
        body.show_chalkboard(chalkboard.drawings)
        language_model = MeteredLanguageModel(
            OllamaLanguageModel(
                client=http_client,
                model=settings.ollama_model,
                generation_options=settings.ollama_generation_options(),
            ),
            budget,
        )

        def start_conversation() -> Conversation:
            return Conversation(
                language_model,
                system_prompt,
                tools=build_capybara_tools(
                    settings, chalkboard, language_model, http_client, body, memory
                ),
                max_steps=settings.max_tool_steps,
                tool_result_reminder=tool_result_reminder,
                tool_result_reminders=TOOL_RESULT_REMINDER_OVERRIDES,
            )

        loop = AutonomousLoop(
            start_conversation,
            budget,
            inner_voice.compose,
            settings.autonomous_cycle_interval_seconds,
            on_thought=print_thought,
            on_cycle_finished=inner_voice.release_offered,
        )
        print(
            f"A capivara está viva. Abra o mundo no Godot (ws://{settings.world_server_host}:"
            f"{settings.world_server_port}). Ctrl+C para encerrar.\n"
        )
        try:
            loop.run()
        except KeyboardInterrupt:
            print("A capivara foi dormir.")


if __name__ == "__main__":
    main()
