"""Builds her conversation with her creator, the same in the terminal chat and in the world."""

import logging
import time
from collections.abc import Callable

import httpx

from src.application.capybara_speech import CapybaraMouth
from src.application.conversation import Conversation
from src.application.creator_chat import CreatorChat
from src.application.creator_presence import CreatorPresence
from src.application.feelings_voice import FeelingsVoice
from src.application.heart import Heart
from src.application.metered_language_model import ChattingAndStructuredLanguageModel
from src.application.voice_mode_switch import VoiceModeSwitch
from src.capybara_tools import TOOL_RESULT_REMINDER_OVERRIDES, build_capybara_tools
from src.domain.discovery_memory import DiscoveryMemory
from src.domain.speech import SpeechError, SpeechSynthesizer
from src.infrastructure.markdown_suggestion_repository import MarkdownSuggestionRepository
from src.infrastructure.prompt_loader import load_prompt
from src.infrastructure.serial_worker import SerialWorker
from src.infrastructure.settings import Settings
from src.infrastructure.websocket_conversation_display import WebSocketConversationDisplay
from src.infrastructure.websocket_voice_output import WebSocketVoiceOutput
from src.infrastructure.world_server import WorldServer

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_NAME = "capybara"
TOOL_RESULT_REMINDER_NAME = "tool_result_reminder"
FEELINGS_TEMPLATE_NAME = "feelings"
SECONDS_PER_MINUTE = 60.0


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


def start_creator_conversation(
    settings: Settings,
    language_model: ChattingAndStructuredLanguageModel,
    http_client: httpx.Client,
    memory: DiscoveryMemory,
    heart: Heart | None,
) -> Conversation:
    """Her tools without a body: while they talk she stays put, facing her creator."""
    return Conversation(
        language_model,
        system_prompt_with_feelings(settings, heart),
        tools=build_capybara_tools(
            settings, language_model, http_client, memory=memory, heart=heart
        ),
        max_steps=settings.max_tool_steps,
        tool_result_reminder=load_prompt(TOOL_RESULT_REMINDER_NAME),
        tool_result_reminders=TOOL_RESULT_REMINDER_OVERRIDES,
    )


def creator_presence(settings: Settings) -> CreatorPresence:
    return CreatorPresence(settings.conversation_quiet_minutes * SECONDS_PER_MINUTE)


def load_world_voice(settings: Settings) -> SpeechSynthesizer | None:
    """Her voice for the world, or None when it cannot be loaded: then she only shows
    captions. Piper is imported here, so the brain runs without the voice extra."""
    try:
        from src.infrastructure.piper_speech_synthesizer import PiperSpeechSynthesizer

        return PiperSpeechSynthesizer.load(settings.voice_model_path)
    except ImportError:
        logger.warning('Her voice is off: install it with pip install ".[voice]"')
    except SpeechError as error:
        logger.warning("Her voice is off: %s", error)
    return None


def build_world_creator_chat(
    conversation: Conversation,
    presence: CreatorPresence,
    world_server: WorldServer,
    heart: Heart | None,
    voice: SpeechSynthesizer | None = None,
    voice_mode: VoiceModeSwitch | None = None,
    world_now: Callable[[], str] | None = None,
) -> CreatorChat:
    mouth = CapybaraMouth(voice, WebSocketVoiceOutput(world_server), voice_mode)
    return CreatorChat(
        conversation,
        presence,
        WebSocketConversationDisplay(world_server),
        mouth,
        heart,
        world_now=world_now,
    )


def listen_to_creator(chat: CreatorChat, worker: SerialWorker) -> Callable[[str], None]:
    """For the world server thread: she stops to listen at once, and the answer is
    written on the worker thread, so the server keeps reading messages meanwhile."""

    def on_creator_said(text: str) -> None:
        print(f"Criador: {text}\n", flush=True)
        chat.hear()
        heard_at = time.monotonic()
        worker.submit(lambda: answer_and_print(text, heard_at))

    def answer_and_print(text: str, heard_at: float) -> None:
        reply = chat.answer(text)
        logger.info("Answered her creator %.1fs after he spoke", time.monotonic() - heard_at)
        if reply is not None:
            print(f"Capivara: {reply}\n", flush=True)

    return on_creator_said
