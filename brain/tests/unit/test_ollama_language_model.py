import json
from collections.abc import Callable

import httpx
import pytest

from src.domain.language_model import ChatMessage, LanguageModelError, Role
from src.infrastructure.ollama_language_model import OllamaLanguageModel

OLLAMA_URL = "http://ollama.test"
MODEL_NAME = "llama3.1:8b"
MESSAGES = [
    ChatMessage(Role.SYSTEM, "You are a curious crow."),
    ChatMessage(Role.USER, "What do you want to research today?"),
]
ASSISTANT_REPLY = "I want to research the stars."

RequestHandler = Callable[[httpx.Request], httpx.Response]


def build_language_model(handler: RequestHandler) -> OllamaLanguageModel:
    client = httpx.Client(base_url=OLLAMA_URL, transport=httpx.MockTransport(handler))
    return OllamaLanguageModel(client=client, model=MODEL_NAME)


@pytest.fixture
def received_requests() -> list[httpx.Request]:
    return []


@pytest.fixture
def healthy_ollama(received_requests: list[httpx.Request]) -> OllamaLanguageModel:
    def reply_successfully(request: httpx.Request) -> httpx.Response:
        received_requests.append(request)
        body = {"message": {"role": "assistant", "content": ASSISTANT_REPLY}}
        return httpx.Response(200, json=body)

    return build_language_model(reply_successfully)


@pytest.fixture
def ollama_with_server_error() -> OllamaLanguageModel:
    return build_language_model(lambda request: httpx.Response(500))


@pytest.fixture
def unreachable_ollama() -> OllamaLanguageModel:
    def refuse_connection(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    return build_language_model(refuse_connection)


@pytest.fixture
def ollama_with_unexpected_response() -> OllamaLanguageModel:
    return build_language_model(lambda request: httpx.Response(200, json={"unexpected": "body"}))


def test_returns_the_assistant_message(healthy_ollama: OllamaLanguageModel) -> None:
    reply = healthy_ollama.chat(MESSAGES)

    assert reply == ChatMessage(Role.ASSISTANT, ASSISTANT_REPLY)


def test_posts_model_and_messages_to_the_chat_endpoint(
    healthy_ollama: OllamaLanguageModel, received_requests: list[httpx.Request]
) -> None:
    healthy_ollama.chat(MESSAGES)

    request = received_requests[0]
    assert request.url.path == "/api/chat"
    assert json.loads(request.content) == {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": "You are a curious crow."},
            {"role": "user", "content": "What do you want to research today?"},
        ],
        "stream": False,
    }


def test_raises_language_model_error_when_server_fails(
    ollama_with_server_error: OllamaLanguageModel,
) -> None:
    with pytest.raises(LanguageModelError):
        ollama_with_server_error.chat(MESSAGES)


def test_raises_language_model_error_when_ollama_is_unreachable(
    unreachable_ollama: OllamaLanguageModel,
) -> None:
    with pytest.raises(LanguageModelError):
        unreachable_ollama.chat(MESSAGES)


def test_raises_language_model_error_when_response_format_is_unexpected(
    ollama_with_unexpected_response: OllamaLanguageModel,
) -> None:
    with pytest.raises(LanguageModelError):
        ollama_with_unexpected_response.chat(MESSAGES)
