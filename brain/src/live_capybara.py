"""Autonomous mode: the capybara lives on her own and her body follows in the Godot world."""

import httpx

from src.application.autonomous_loop import AutonomousLoop
from src.application.conversation import Conversation
from src.application.inner_voice import InnerVoice
from src.application.metered_language_model import MeteredLanguageModel
from src.application.token_budget import HourlyTokenBudget
from src.capybara_tools import TOOL_RESULT_REMINDER_OVERRIDES, build_capybara_tools
from src.domain.chalkboard import Chalkboard
from src.infrastructure.logging_setup import configure_logging
from src.infrastructure.markdown_discovery_repository import MarkdownDiscoveryRepository
from src.infrastructure.ollama_language_model import OllamaLanguageModel
from src.infrastructure.prompt_loader import load_prompt
from src.infrastructure.settings import Settings
from src.infrastructure.websocket_body import WebSocketBody
from src.infrastructure.world_server import WorldServer

SYSTEM_PROMPT_NAME = "capybara"
TOOL_RESULT_REMINDER_NAME = "tool_result_reminder"
INNER_VOICE_NAME = "autonomous_cycle"
MEMORY_TEMPLATE_NAME = "known_discoveries"


def print_thought(thought: str) -> None:
    print(f"Capivara (pensando): {thought}\n", flush=True)


def main() -> None:
    settings = Settings()
    configure_logging(settings.log_file, settings.log_level)
    budget = HourlyTokenBudget(settings.max_tokens_per_hour)
    chalkboard = Chalkboard(settings.chalkboard_capacity)
    system_prompt = load_prompt(SYSTEM_PROMPT_NAME)
    tool_result_reminder = load_prompt(TOOL_RESULT_REMINDER_NAME)
    inner_voice = InnerVoice(
        invitation=load_prompt(INNER_VOICE_NAME),
        catalog=MarkdownDiscoveryRepository(settings.discoveries_dir),
        memory_template=load_prompt(MEMORY_TEMPLATE_NAME),
        max_remembered_discoveries=settings.max_remembered_discoveries,
    )
    with (
        WorldServer(settings.world_server_host, settings.world_server_port) as world_server,
        httpx.Client(
            base_url=settings.ollama_base_url, timeout=settings.ollama_timeout_seconds
        ) as http_client,
    ):
        body = WebSocketBody(world_server)
        body.show_chalkboard(chalkboard.drawings)
        language_model = MeteredLanguageModel(
            OllamaLanguageModel(
                client=http_client,
                model=settings.ollama_model,
                generation_options=settings.ollama_generation_options(),
                structured_num_predict=settings.ollama_structured_num_predict,
            ),
            budget,
        )

        def start_conversation() -> Conversation:
            return Conversation(
                language_model,
                system_prompt,
                tools=build_capybara_tools(settings, chalkboard, body),
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
