from collections.abc import Sequence
from datetime import date
from pathlib import Path

import pytest

from src.application.conversation import Conversation
from src.application.tools.save_discovery_tool import SaveDiscoveryTool
from src.domain.language_model import ChatMessage, Role, ToolCall, ToolDefinition
from src.infrastructure.markdown_discovery_repository import MarkdownDiscoveryRepository

SYSTEM_PROMPT = "You are a curious capybara."
USER_MESSAGE = "Você sabia que capivaras nadam?"
FINAL_ANSWER = "Guardei isso no meu tesouro!"
TODAY = date(2026, 11, 22)
EXPECTED_FILE_NAME = "2026-11-22-capivaras-nadam.md"
SAVE_REQUEST = ToolCall(
    name="save_discovery",
    arguments={
        "title": "Capivaras nadam",
        "topic": "capivaras",
        "summary": "Eu sei prender a respiração por cinco minutos!",
        "sources": ["https://example.com/swim"],
    },
)


class ScriptedLanguageModel:
    """Asks to save a discovery first, then gives the final answer."""

    def __init__(self) -> None:
        self._replies = iter(
            [
                ChatMessage(Role.ASSISTANT, "", tool_calls=(SAVE_REQUEST,)),
                ChatMessage(Role.ASSISTANT, FINAL_ANSWER),
            ]
        )
        self.received_histories: list[list[ChatMessage]] = []

    def chat(
        self,
        messages: list[ChatMessage],
        tools: Sequence[ToolDefinition] = (),
    ) -> ChatMessage:
        self.received_histories.append(messages)
        return next(self._replies)


@pytest.fixture
def language_model() -> ScriptedLanguageModel:
    return ScriptedLanguageModel()


@pytest.fixture
def conversation(language_model: ScriptedLanguageModel, tmp_path: Path) -> Conversation:
    save_discovery_tool = SaveDiscoveryTool(
        MarkdownDiscoveryRepository(tmp_path), today=lambda: TODAY
    )
    return Conversation(language_model, SYSTEM_PROMPT, tools=[save_discovery_tool])


def test_writes_the_discovery_file_when_the_model_asks_to_save(
    conversation: Conversation, tmp_path: Path
) -> None:
    conversation.send(USER_MESSAGE)

    content = (tmp_path / EXPECTED_FILE_NAME).read_text(encoding="utf-8")
    assert "Eu sei prender a respiração por cinco minutos!" in content


def test_tells_the_model_where_the_discovery_was_saved(
    conversation: Conversation, language_model: ScriptedLanguageModel
) -> None:
    conversation.send(USER_MESSAGE)

    tool_result = language_model.received_histories[1][-1]
    assert tool_result == ChatMessage(
        Role.TOOL, f"Saved as {EXPECTED_FILE_NAME}", tool_name="save_discovery"
    )


def test_returns_the_final_answer_after_saving(conversation: Conversation) -> None:
    assert conversation.send(USER_MESSAGE) == FINAL_ANSWER
