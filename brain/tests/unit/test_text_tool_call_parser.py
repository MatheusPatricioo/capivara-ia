from src.domain.language_model import ToolCall
from src.infrastructure.text_tool_call_parser import find_tool_call_in_text

TOOL_NAMES = {"web_search", "save_discovery"}
SEARCH_CALL = ToolCall(name="web_search", arguments={"query": "estrelas"})


def test_finds_a_tool_call_written_after_some_text() -> None:
    text = (
        "Vou pesquisar sobre estrelas!\n\n"
        ' Ronaldo {"name": "web_search", "arguments": {"query": "estrelas"}}'
    )

    assert find_tool_call_in_text(text, TOOL_NAMES) == SEARCH_CALL


def test_keeps_only_the_first_call_when_the_model_invents_the_next_steps() -> None:
    text = (
        '{"name": "web_search", "arguments": {"query": "estrelas"}}\n'
        "Achei muita coisa!\n"
        '{"name": "save_discovery", "arguments": {"title": "Estrelas"}}'
    )

    assert find_tool_call_in_text(text, TOOL_NAMES) == SEARCH_CALL


def test_finds_the_call_after_a_brace_that_is_not_json() -> None:
    text = 'Fiz uma carinha {: e agora {"name": "web_search", "arguments": {"query": "estrelas"}}'

    assert find_tool_call_in_text(text, TOOL_NAMES) == SEARCH_CALL


def test_returns_none_for_plain_text() -> None:
    assert find_tool_call_in_text("Hoje vou só descansar no laguinho.", TOOL_NAMES) is None


def test_returns_none_for_an_unknown_tool_name() -> None:
    text = '{"name": "delete_files", "arguments": {"path": "C:/"}}'

    assert find_tool_call_in_text(text, TOOL_NAMES) is None


def test_returns_none_when_the_arguments_are_not_an_object() -> None:
    text = '{"name": "web_search", "arguments": "estrelas"}'

    assert find_tool_call_in_text(text, TOOL_NAMES) is None


def test_returns_none_for_a_call_cut_off_in_the_middle() -> None:
    text = '{"name": "web_search", "arguments": {"query": "estre'

    assert find_tool_call_in_text(text, TOOL_NAMES) is None
