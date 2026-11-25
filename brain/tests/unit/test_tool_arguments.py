import pytest
from pydantic import Field

from src.application.tools.tool_arguments import (
    NonEmptyText,
    ToolArguments,
    parse_arguments,
    tool_parameters,
)
from src.domain.tool import ToolError


class NoteArguments(ToolArguments):
    title: NonEmptyText = Field(description="The note title.")
    tags: list[str] = Field(default_factory=list, description="Words to find it later.")


def test_the_schema_describes_each_field() -> None:
    schema = tool_parameters(NoteArguments)

    assert schema["properties"] == {
        "title": {"type": "string", "minLength": 1, "description": "The note title."},
        "tags": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Words to find it later.",
        },
    }


def test_the_schema_lists_the_required_fields() -> None:
    assert tool_parameters(NoteArguments)["required"] == ["title"]


def test_the_schema_leaves_out_the_titles_pydantic_adds() -> None:
    assert "title" not in tool_parameters(NoteArguments)


def test_parses_valid_arguments_removing_surrounding_spaces() -> None:
    parsed = parse_arguments(NoteArguments, {"title": "  Lua  ", "tags": ["céu"]})

    assert parsed == NoteArguments(title="Lua", tags=["céu"])


def test_ignores_arguments_nobody_asked_for() -> None:
    parsed = parse_arguments(NoteArguments, {"title": "Lua", "mood": "happy"})

    assert parsed == NoteArguments(title="Lua")


def test_says_a_missing_field_is_required() -> None:
    with pytest.raises(ToolError, match="'title' is required"):
        parse_arguments(NoteArguments, {})


def test_says_a_blank_text_must_not_be_empty() -> None:
    with pytest.raises(ToolError, match="'title' must not be empty"):
        parse_arguments(NoteArguments, {"title": "   "})


def test_does_not_accept_a_number_as_text() -> None:
    with pytest.raises(ToolError, match="'title' must be a text"):
        parse_arguments(NoteArguments, {"title": 7})


def test_names_every_wrong_field_in_one_message() -> None:
    with pytest.raises(ToolError, match="'title' is required; 'tags' must be a list"):
        parse_arguments(NoteArguments, {"tags": "céu"})
