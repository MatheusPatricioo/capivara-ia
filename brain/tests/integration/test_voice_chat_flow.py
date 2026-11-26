from collections.abc import Sequence

import pytest

from src.application.capybara_speech import CapybaraMouth, CapybaraSpeech, SpeakerOutput
from src.application.conversation import Conversation
from src.domain.language_model import ChatMessage, Role, ToolDefinition
from tests.fakes.speech import (
    RecordingSpeaker,
    RecordingSynthesizer,
    ScriptedRecognizer,
    recording_of,
)

SYSTEM_PROMPT = "Você é uma capivara curiosa."
SPOKEN_QUESTION = "O que você descobriu hoje?"
WRITTEN_REPLY = "Descobri que **capivaras** nadam muito bem! 🦫"
SPOKEN_REPLY = "Descobri que capivaras nadam muito bem!"


class RecordingLanguageModel:
    def __init__(self) -> None:
        self.received_histories: list[list[ChatMessage]] = []

    def chat(
        self,
        messages: list[ChatMessage],
        tools: Sequence[ToolDefinition] = (),
    ) -> ChatMessage:
        self.received_histories.append(messages)
        return ChatMessage(Role.ASSISTANT, WRITTEN_REPLY)


@pytest.fixture
def language_model() -> RecordingLanguageModel:
    return RecordingLanguageModel()


@pytest.fixture
def speaker() -> RecordingSpeaker:
    return RecordingSpeaker()


@pytest.fixture
def speech(speaker: RecordingSpeaker) -> CapybaraSpeech:
    mouth = CapybaraMouth(RecordingSynthesizer(), SpeakerOutput(speaker))
    return CapybaraSpeech(ScriptedRecognizer(), mouth)


@pytest.fixture
def reply_to_spoken_question(language_model: RecordingLanguageModel, speech: CapybaraSpeech) -> str:
    """One spoken turn, as the chat runs it: hear, send the text, say the reply."""
    conversation = Conversation(language_model, SYSTEM_PROMPT)
    heard_question = speech.hear(recording_of(SPOKEN_QUESTION))
    reply = conversation.send(heard_question)
    speech.say(reply)
    return reply


def test_the_spoken_question_reaches_the_model_as_text(
    reply_to_spoken_question: str, language_model: RecordingLanguageModel
) -> None:
    last_message = language_model.received_histories[0][-1]

    assert last_message == ChatMessage(Role.USER, SPOKEN_QUESTION)


def test_the_written_reply_keeps_its_markdown_for_the_screen(reply_to_spoken_question: str) -> None:
    assert reply_to_spoken_question == WRITTEN_REPLY


def test_the_reply_is_said_out_loud_without_markdown_or_emojis(
    reply_to_spoken_question: str, speaker: RecordingSpeaker
) -> None:
    assert speaker.played_audios == [recording_of(SPOKEN_REPLY)]
