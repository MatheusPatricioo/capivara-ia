import sys

import httpx

from src.application.ask_question import AskQuestion
from src.domain.language_model import LanguageModelError
from src.infrastructure.ollama_language_model import OllamaLanguageModel
from src.infrastructure.prompt_loader import load_prompt
from src.infrastructure.settings import Settings

SYSTEM_PROMPT_NAME = "capybara"
QUESTION = "O que você quer pesquisar hoje?"


def main() -> None:
    settings = Settings()
    with httpx.Client(
        base_url=settings.ollama_base_url,
        timeout=settings.ollama_timeout_seconds,
    ) as http_client:
        language_model = OllamaLanguageModel(
            client=http_client,
            model=settings.ollama_model,
            generation_options=settings.ollama_generation_options(),
        )
        ask_question = AskQuestion(language_model)
        try:
            reply = ask_question.execute(
                system_prompt=load_prompt(SYSTEM_PROMPT_NAME),
                question=QUESTION,
            )
        except LanguageModelError as error:
            print(f"The capybara could not think: {error}", file=sys.stderr)
            raise SystemExit(1) from error
    print(reply)


if __name__ == "__main__":
    main()
