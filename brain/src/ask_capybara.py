import sys

import httpx

from src.application.ask_question import AskQuestion
from src.domain.language_model import LanguageModelError
from src.infrastructure.ollama_language_model import OllamaLanguageModel
from src.infrastructure.settings import Settings

SYSTEM_PROMPT = "Você é uma capivara curiosa"
QUESTION = "O que você quer pesquisar hoje?"


def main() -> None:
    settings = Settings()
    with httpx.Client(
        base_url=settings.ollama_base_url,
        timeout=settings.ollama_timeout_seconds,
    ) as http_client:
        language_model = OllamaLanguageModel(client=http_client, model=settings.ollama_model)
        ask_question = AskQuestion(language_model)
        try:
            reply = ask_question.execute(system_prompt=SYSTEM_PROMPT, question=QUESTION)
        except LanguageModelError as error:
            print(f"The capybara could not think: {error}", file=sys.stderr)
            raise SystemExit(1) from error
    print(reply)


if __name__ == "__main__":
    main()
