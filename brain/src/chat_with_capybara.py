import sys

import httpx

from src.application.conversation import Conversation, StepLimitReachedError
from src.application.feelings_voice import FeelingsVoice
from src.application.heart import Heart
from src.capybara_heart import build_heart
from src.capybara_tools import TOOL_RESULT_REMINDER_OVERRIDES, build_capybara_tools
from src.domain.feelings.appraisal import EmotionalEvent, EventKind
from src.domain.language_model import LanguageModelError
from src.infrastructure.logging_setup import configure_logging
from src.infrastructure.markdown_suggestion_repository import MarkdownSuggestionRepository
from src.infrastructure.ollama_language_model import OllamaLanguageModel
from src.infrastructure.prompt_loader import load_prompt
from src.infrastructure.settings import Settings
from src.long_term_memory import open_long_term_memory

SYSTEM_PROMPT_NAME = "capybara"
TOOL_RESULT_REMINDER_NAME = "tool_result_reminder"
EXIT_COMMAND = "sair"
FEELINGS_TEMPLATE_NAME = "feelings"


def system_prompt_with_feelings(settings: Settings, heart: Heart | None) -> str:
    """How she feels when the chat opens, before the first message: after days alone she
    greets Matheus with what those days did to her. Read once, at the start."""
    system_prompt = load_prompt(SYSTEM_PROMPT_NAME)
    if heart is None:
        return system_prompt
    feelings = FeelingsVoice(
        heart,
        load_prompt(FEELINGS_TEMPLATE_NAME),
        MarkdownSuggestionRepository(settings.discoveries_dir),
    )
    return f"{system_prompt}\n\n{feelings.compose()}"


def main() -> None:
    settings = Settings()
    configure_logging(settings.log_file, settings.log_level)
    heart = build_heart(settings)
    with (
        httpx.Client(
            base_url=settings.ollama_base_url,
            timeout=settings.ollama_timeout_seconds,
        ) as http_client,
        open_long_term_memory(settings, http_client) as memory,
    ):
        language_model = OllamaLanguageModel(
            client=http_client,
            model=settings.ollama_model,
            generation_options=settings.ollama_generation_options(),
        )
        conversation = Conversation(
            language_model,
            system_prompt_with_feelings(settings, heart),
            tools=build_capybara_tools(
                settings,
                language_model,
                http_client,
                memory=memory,
                heart=heart,
            ),
            max_steps=settings.max_tool_steps,
            tool_result_reminder=load_prompt(TOOL_RESULT_REMINDER_NAME),
            tool_result_reminders=TOOL_RESULT_REMINDER_OVERRIDES,
        )
        print(f'Converse com a capivara. Digite "{EXIT_COMMAND}" para encerrar.')
        while True:
            user_input = input("Você: ").strip()
            if user_input.lower() == EXIT_COMMAND:
                break
            if not user_input:
                continue
            if heart is not None:
                heart.feel(EmotionalEvent(EventKind.TALKED_WITH_MATHEUS))
            try:
                reply = conversation.send(user_input)
            except (LanguageModelError, StepLimitReachedError) as error:
                print(f"The capybara could not think: {error}", file=sys.stderr)
                continue
            print(f"Capivara: {reply}")


if __name__ == "__main__":
    main()
