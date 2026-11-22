import sys

import httpx

from src.application.conversation import Conversation, StepLimitReachedError
from src.domain.language_model import LanguageModelError
from src.infrastructure.ollama_language_model import OllamaLanguageModel
from src.infrastructure.settings import Settings

SYSTEM_PROMPT = "Você é uma capivara curiosa"
EXIT_COMMAND = "sair"


def main() -> None:
    settings = Settings()
    with httpx.Client(
        base_url=settings.ollama_base_url,
        timeout=settings.ollama_timeout_seconds,
    ) as http_client:
        language_model = OllamaLanguageModel(client=http_client, model=settings.ollama_model)
        conversation = Conversation(
            language_model,
            SYSTEM_PROMPT,
            max_steps=settings.max_tool_steps,
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
