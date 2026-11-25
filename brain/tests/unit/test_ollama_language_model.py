import json
from collections.abc import Callable

import httpx
import pytest

from src.domain.language_model import (
    ChatMessage,
    LanguageModelError,
    Role,
    StructuredReply,
    ToolCall,
    ToolDefinition,
)
from src.infrastructure.ollama_language_model import (
    OllamaGenerationOptions,
    OllamaLanguageModel,
)

OLLAMA_URL = "http://ollama.test"
MODEL_NAME = "llama3.1:8b"
MESSAGES = [
    ChatMessage(Role.SYSTEM, "You are a curious capybara."),
    ChatMessage(Role.USER, "What do you want to research today?"),
]
ASSISTANT_REPLY = "I want to research the stars."
GENERATION_OPTIONS = OllamaGenerationOptions(num_predict=300, temperature=0.8, repeat_penalty=1.1)
SEARCH_TOOL = ToolDefinition(
    name="web_search",
    description="Searches the web.",
    parameters={"type": "object", "properties": {"query": {"type": "string"}}},
)
SEARCH_CALL = ToolCall(name="web_search", arguments={"query": "stars"})
MESSAGES_WITH_TOOL_ROUND_TRIP = [
    *MESSAGES,
    ChatMessage(Role.ASSISTANT, "", tool_calls=(SEARCH_CALL,)),
    ChatMessage(Role.TOOL, "Stars are suns.", tool_name="web_search"),
]

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
def ollama_asking_for_a_tool() -> OllamaLanguageModel:
    body = {
        "message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [{"function": {"name": "web_search", "arguments": {"query": "stars"}}}],
        }
    }
    return build_language_model(lambda request: httpx.Response(200, json=body))


@pytest.fixture
def ollama_with_malformed_tool_call() -> OllamaLanguageModel:
    body = {
        "message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [{"function": {"name": "web_search", "arguments": "not an object"}}],
        }
    }
    return build_language_model(lambda request: httpx.Response(200, json=body))


TOOL_CALL_WRITTEN_AS_TEXT = (
    'Vou pesquisar!\n Ronaldo {"name": "web_search", "arguments": {"query": "stars"}}\n'
    "Achei estrelas gemeas!"
)


@pytest.fixture
def ollama_writing_the_tool_call_as_text() -> OllamaLanguageModel:
    body = {"message": {"role": "assistant", "content": TOOL_CALL_WRITTEN_AS_TEXT}}
    return build_language_model(lambda request: httpx.Response(200, json=body))


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
            {"role": "system", "content": "You are a curious capybara."},
            {"role": "user", "content": "What do you want to research today?"},
        ],
        "stream": False,
    }


def test_sends_the_generation_options(received_requests: list[httpx.Request]) -> None:
    def reply_successfully(request: httpx.Request) -> httpx.Response:
        received_requests.append(request)
        return httpx.Response(200, json={"message": {"role": "assistant", "content": "Hi"}})

    client = httpx.Client(base_url=OLLAMA_URL, transport=httpx.MockTransport(reply_successfully))
    language_model = OllamaLanguageModel(
        client=client, model=MODEL_NAME, generation_options=GENERATION_OPTIONS
    )

    language_model.chat(MESSAGES)

    assert json.loads(received_requests[0].content)["options"] == {
        "num_predict": 300,
        "temperature": 0.8,
        "repeat_penalty": 1.1,
    }


def test_sends_tool_definitions_in_the_ollama_format(
    healthy_ollama: OllamaLanguageModel, received_requests: list[httpx.Request]
) -> None:
    healthy_ollama.chat(MESSAGES, tools=[SEARCH_TOOL])

    assert json.loads(received_requests[0].content)["tools"] == [
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Searches the web.",
                "parameters": {"type": "object", "properties": {"query": {"type": "string"}}},
            },
        }
    ]


def test_sends_tool_requests_and_results_from_the_history(
    healthy_ollama: OllamaLanguageModel, received_requests: list[httpx.Request]
) -> None:
    healthy_ollama.chat(MESSAGES_WITH_TOOL_ROUND_TRIP)

    assert json.loads(received_requests[0].content)["messages"][-2:] == [
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [{"function": {"name": "web_search", "arguments": {"query": "stars"}}}],
        },
        {"role": "tool", "content": "Stars are suns.", "tool_name": "web_search"},
    ]


def test_returns_the_tool_calls_requested_by_the_model(
    ollama_asking_for_a_tool: OllamaLanguageModel,
) -> None:
    reply = ollama_asking_for_a_tool.chat(MESSAGES, tools=[SEARCH_TOOL])

    assert reply == ChatMessage(Role.ASSISTANT, "", tool_calls=(SEARCH_CALL,))


def test_raises_language_model_error_when_tool_call_is_malformed(
    ollama_with_malformed_tool_call: OllamaLanguageModel,
) -> None:
    with pytest.raises(LanguageModelError):
        ollama_with_malformed_tool_call.chat(MESSAGES, tools=[SEARCH_TOOL])


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


def test_reports_the_tokens_read_and_written() -> None:
    def reply_with_token_counts(request: httpx.Request) -> httpx.Response:
        body = {
            "message": {"role": "assistant", "content": ASSISTANT_REPLY},
            "prompt_eval_count": 1200,
            "eval_count": 80,
        }
        return httpx.Response(200, json=body)

    reply = build_language_model(reply_with_token_counts).chat(MESSAGES)

    assert reply.token_count == 1280


def test_reports_zero_tokens_when_ollama_omits_the_counts(
    healthy_ollama: OllamaLanguageModel,
) -> None:
    assert healthy_ollama.chat(MESSAGES).token_count == 0


def test_recovers_a_tool_call_written_as_text(
    ollama_writing_the_tool_call_as_text: OllamaLanguageModel,
) -> None:
    reply = ollama_writing_the_tool_call_as_text.chat(MESSAGES, tools=[SEARCH_TOOL])

    assert reply == ChatMessage(Role.ASSISTANT, "", tool_calls=(SEARCH_CALL,))


def test_counts_each_tool_call_recovered_from_text(
    ollama_writing_the_tool_call_as_text: OllamaLanguageModel,
) -> None:
    ollama_writing_the_tool_call_as_text.chat(MESSAGES, tools=[SEARCH_TOOL])
    ollama_writing_the_tool_call_as_text.chat(MESSAGES, tools=[SEARCH_TOOL])

    assert ollama_writing_the_tool_call_as_text.recovered_tool_call_count == 2


def test_does_not_count_native_tool_calls_as_recovered(
    ollama_asking_for_a_tool: OllamaLanguageModel,
) -> None:
    ollama_asking_for_a_tool.chat(MESSAGES, tools=[SEARCH_TOOL])

    assert ollama_asking_for_a_tool.recovered_tool_call_count == 0


def test_keeps_the_text_when_no_tools_were_offered(
    ollama_writing_the_tool_call_as_text: OllamaLanguageModel,
) -> None:
    reply = ollama_writing_the_tool_call_as_text.chat(MESSAGES)

    assert reply == ChatMessage(Role.ASSISTANT, TOOL_CALL_WRITTEN_AS_TEXT)


def test_keeps_a_plain_answer_when_tools_were_offered(
    healthy_ollama: OllamaLanguageModel,
) -> None:
    reply = healthy_ollama.chat(MESSAGES, tools=[SEARCH_TOOL])

    assert reply == ChatMessage(Role.ASSISTANT, ASSISTANT_REPLY)


CHOICE_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {"category": {"type": "string"}},
    "required": ["category"],
}


def ollama_answering_with(content: str, **extra_fields: int) -> OllamaLanguageModel:
    body = {"message": {"role": "assistant", "content": content}, **extra_fields}
    return build_language_model(lambda request: httpx.Response(200, json=body))


def test_sends_the_schema_as_the_ollama_format(
    received_requests: list[httpx.Request],
) -> None:
    def reply_with_json(request: httpx.Request) -> httpx.Response:
        received_requests.append(request)
        body = {"message": {"role": "assistant", "content": '{"category": "cat"}'}}
        return httpx.Response(200, json=body)

    build_language_model(reply_with_json).complete_json(MESSAGES, CHOICE_SCHEMA)

    assert json.loads(received_requests[0].content)["format"] == CHOICE_SCHEMA


def test_returns_the_parsed_json_object() -> None:
    language_model = ollama_answering_with('{"category": "cat"}')

    reply = language_model.complete_json(MESSAGES, CHOICE_SCHEMA)

    assert reply == StructuredReply(data={"category": "cat"})


def test_reports_the_tokens_of_the_structured_reply() -> None:
    language_model = ollama_answering_with(
        '{"category": "nenhuma"}', prompt_eval_count=300, eval_count=20
    )

    reply = language_model.complete_json(MESSAGES, CHOICE_SCHEMA)

    assert reply.token_count == 320


def test_raises_language_model_error_when_the_json_is_invalid() -> None:
    language_model = ollama_answering_with('{"category": "ca')

    with pytest.raises(LanguageModelError):
        language_model.complete_json(MESSAGES, CHOICE_SCHEMA)


def test_raises_language_model_error_when_the_json_is_not_an_object() -> None:
    language_model = ollama_answering_with('["cat"]')

    with pytest.raises(LanguageModelError):
        language_model.complete_json(MESSAGES, CHOICE_SCHEMA)


def test_raises_language_model_error_when_the_structured_call_fails(
    ollama_with_server_error: OllamaLanguageModel,
) -> None:
    with pytest.raises(LanguageModelError):
        ollama_with_server_error.complete_json(MESSAGES, CHOICE_SCHEMA)


def test_structured_replies_always_take_the_most_likely_answer(
    received_requests: list[httpx.Request],
) -> None:
    def reply_with_json(request: httpx.Request) -> httpx.Response:
        received_requests.append(request)
        body = {"message": {"role": "assistant", "content": '{"category": "cat"}'}}
        return httpx.Response(200, json=body)

    client = httpx.Client(base_url=OLLAMA_URL, transport=httpx.MockTransport(reply_with_json))
    language_model = OllamaLanguageModel(
        client=client, model=MODEL_NAME, generation_options=GENERATION_OPTIONS
    )

    language_model.complete_json(MESSAGES, CHOICE_SCHEMA)

    assert json.loads(received_requests[0].content)["options"] == {
        "num_predict": 300,
        "temperature": 0.0,
        "repeat_penalty": 1.1,
    }


def test_chat_replies_keep_the_configured_temperature(
    received_requests: list[httpx.Request],
) -> None:
    def reply_with_text(request: httpx.Request) -> httpx.Response:
        received_requests.append(request)
        return httpx.Response(200, json={"message": {"role": "assistant", "content": "Oi!"}})

    client = httpx.Client(base_url=OLLAMA_URL, transport=httpx.MockTransport(reply_with_text))
    language_model = OllamaLanguageModel(
        client=client, model=MODEL_NAME, generation_options=GENERATION_OPTIONS
    )

    language_model.chat(MESSAGES)

    assert json.loads(received_requests[0].content)["options"]["temperature"] == 0.8
