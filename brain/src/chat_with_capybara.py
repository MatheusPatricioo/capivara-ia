import sys

import httpx

from src.application.conversation import Conversation, StepLimitReachedError
from src.capybara_tools import build_capybara_tools
from src.domain.chalkboard import Chalkboard
from src.domain.language_model import LanguageModelError
from src.infrastructure.logging_setup import configure_logging
from src.infrastructure.ollama_language_model import OllamaLanguageModel
from src.infrastructure.prompt_loader import load_prompt
from src.infrastructure.settings import Settings

SYSTEM_PROMPT_NAME = "capybara"
TOOL_RESULT_REMINDER_NAME = "tool_result_reminder"
EXIT_COMMAND = "sair"


def main() -> None:
    settings = Settings()
    configure_logging(settings.log_file, settings.log_level)
    with httpx.Client(
        base_url=settings.ollama_base_url,
        timeout=settings.ollama_timeout_seconds,
    ) as http_client:
        language_model = OllamaLanguageModel(
            client=http_client,
            model=settings.ollama_model,
            generation_options=settings.ollama_generation_options(),
        )
        conversation = Conversation(
            language_model,
            load_prompt(SYSTEM_PROMPT_NAME),
            tools=build_capybara_tools(settings, Chalkboard(settings.chalkboard_capacity)),
            max_steps=settings.max_tool_steps,
            tool_result_reminder=load_prompt(TOOL_RESULT_REMINDER_NAME),
        )
        print(f'Converse com a capivara. Digite "{EXIT_COMMAND}" para encerrar.')
        while True:
            user_input = input("Você: ").strip()
            if user_input.lower() == EXIT_COMMAND:
                break
            if not user_input:
                continue
            try:
                reply = conversation.send(user_input)
            except (LanguageModelError, StepLimitReachedError) as error:
                print(f"The capybara could not think: {error}", file=sys.stderr)
                continue
            print(f"Capivara: {reply}")


if __name__ == "__main__":
    main()
