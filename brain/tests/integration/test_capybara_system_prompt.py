import json
from typing import Any

import httpx
import pytest

from src.application.conversation import Conversation
from src.infrastructure.ollama_language_model import OllamaLanguageModel
from src.infrastructure.prompt_loader import PROMPTS_DIR, load_prompt

OLLAMA_URL = "http://ollama.test"
MODEL_NAME = "llama3.1:8b"
GREETING = "Oi, capivara!"
REPLY = "Oi, criador!"


class RecordingOllamaServer:
    """Answers every chat request and keeps the JSON payloads it received."""

    def __init__(self) -> None:
        self.received_payloads: list[dict[str, Any]] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.received_payloads.append(json.loads(request.content))
        return httpx.Response(200, json={"message": {"role": "assistant", "content": REPLY}})


@pytest.fixture
def ollama_server() -> RecordingOllamaServer:
    return RecordingOllamaServer()


@pytest.fixture
def capybara_conversation(ollama_server: RecordingOllamaServer) -> Conversation:
    client = httpx.Client(base_url=OLLAMA_URL, transport=httpx.MockTransport(ollama_server.handle))
    language_model = OllamaLanguageModel(client=client, model=MODEL_NAME)
    return Conversation(language_model, load_prompt("capybara"))


def test_sends_the_capybara_prompt_file_as_the_first_system_message(
    capybara_conversation: Conversation, ollama_server: RecordingOllamaServer
) -> None:
    capybara_conversation.send(GREETING)

    prompt_file_text = (PROMPTS_DIR / "capybara.md").read_text(encoding="utf-8").strip()
    first_message = ollama_server.received_payloads[0]["messages"][0]
    assert first_message == {"role": "system", "content": prompt_file_text}
