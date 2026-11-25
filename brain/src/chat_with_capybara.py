import argparse
import sys
from collections.abc import Sequence
from typing import TYPE_CHECKING

import httpx

from src.application.conversation import Conversation, StepLimitReachedError
from src.application.feelings_voice import FeelingsVoice
from src.application.heart import Heart
from src.capybara_heart import build_heart
from src.capybara_tools import TOOL_RESULT_REMINDER_OVERRIDES, build_capybara_tools
from src.domain.feelings.appraisal import EmotionalEvent, EventKind
from src.domain.language_model import LanguageModelError
from src.domain.speech import SpeechError
from src.infrastructure.logging_setup import configure_logging
from src.infrastructure.markdown_suggestion_repository import MarkdownSuggestionRepository
from src.infrastructure.ollama_language_model import OllamaLanguageModel
from src.infrastructure.prompt_loader import load_prompt
from src.infrastructure.settings import Settings
from src.long_term_memory import open_long_term_memory

if TYPE_CHECKING:
    # Only for the type checker: at run time the voice is imported when --voz asks for it.
    from src.capybara_voice import CapybaraVoice

SYSTEM_PROMPT_NAME = "capybara"
TOOL_RESULT_REMINDER_NAME = "tool_result_reminder"
EXIT_COMMAND = "sair"
FEELINGS_TEMPLATE_NAME = "feelings"
TEXT_PROMPT = "Você: "
VOICE_PROMPT = "Você (ou Enter vazio para falar): "
LISTENING_PROMPT = "[ouvindo... aperte Enter quando terminar de falar]"
VOICE_INSTALL_HINT = 'instale as bibliotecas de voz com: pip install ".[voice]"'


def parse_arguments(arguments: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m src.chat_with_capybara",
        description="Converse com a capivara pelo terminal.",
    )
    parser.add_argument(
        "--voz",
        dest="voice",
        action="store_true",
        help="ela fala as respostas em voz alta, e um Enter vazio grava a sua fala no microfone",
    )
    return parser.parse_args(arguments)


def system_prompt_with_feelings(settings: Settings, heart: Heart | None) -> str:
    """How she feels when the chat opens, before the first message: after days alone she
    greets her creator with what those days did to her. Read once, at the start."""
    system_prompt = load_prompt(SYSTEM_PROMPT_NAME)
    if heart is None:
        return system_prompt
    feelings = FeelingsVoice(
        heart,
        load_prompt(FEELINGS_TEMPLATE_NAME),
        MarkdownSuggestionRepository(settings.discoveries_dir),
    )
    return f"{system_prompt}\n\n{feelings.compose()}"


def load_voice(settings: Settings) -> "CapybaraVoice | None":
    """Her voice, or None when it cannot load: then the chat goes on in text only."""
    print("Carregando a voz (na primeira vez, o modelo de fala é baixado)...")
    try:
        from src.capybara_voice import build_capybara_voice

        return build_capybara_voice(settings)
    except ModuleNotFoundError:
        print(f"Sem voz desta vez: {VOICE_INSTALL_HINT}", file=sys.stderr)
    except SpeechError as error:
        print(f"Sem voz desta vez: {error}", file=sys.stderr)
    return None


def listen(voice: "CapybaraVoice") -> str:
    """Push to talk: records from the first Enter until the next one."""
    voice.microphone.start_recording()
    input(LISTENING_PROMPT)
    heard = voice.speech.hear(voice.microphone.stop_recording())
    if heard:
        print(f"Você (falando): {heard}")
    else:
        print("(Não ouvi nada. Tente de novo.)")
    return heard


def read_user_message(voice: "CapybaraVoice | None") -> str:
    """What her creator typed or, with the voice on, said after an empty Enter."""
    if voice is None:
        return input(TEXT_PROMPT).strip()
    typed = input(VOICE_PROMPT).strip()
    if typed:
        return typed
    try:
        return listen(voice)
    except SpeechError as error:
        print(f"Não consegui ouvir: {error}", file=sys.stderr)
        return ""


def chat(conversation: Conversation, heart: Heart | None, voice: "CapybaraVoice | None") -> None:
    print(f'Converse com a capivara. Digite "{EXIT_COMMAND}" para encerrar.')
    while True:
        user_message = read_user_message(voice)
        if user_message.lower() == EXIT_COMMAND:
            break
        if not user_message:
            continue
        if heart is not None:
            heart.feel(EmotionalEvent(EventKind.TALKED_WITH_MATHEUS))
        try:
            reply = conversation.send(user_message)
        except (LanguageModelError, StepLimitReachedError) as error:
            print(f"The capybara could not think: {error}", file=sys.stderr)
            continue
        print(f"Capivara: {reply}")
        if voice is not None:
            voice.speech.say(reply)


def main() -> None:
    arguments = parse_arguments(sys.argv[1:])
    settings = Settings()
    configure_logging(settings.log_file, settings.log_level)
    voice = load_voice(settings) if arguments.voice else None
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
        chat(conversation, heart, voice)


if __name__ == "__main__":
    main()
