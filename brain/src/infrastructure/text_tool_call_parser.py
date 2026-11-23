import json
from collections.abc import Collection

from src.domain.language_model import ToolCall

JSON_OBJECT_START = "{"


def find_tool_call_in_text(text: str, tool_names: Collection[str]) -> ToolCall | None:
    """Finds the first tool call that a model wrote as plain text instead of a real tool call.

    Small local models sometimes lose the special token that marks a tool call and print
    the JSON {"name": ..., "arguments": {...}} in the middle of their answer. Only a known
    tool name with an object of arguments counts, so ordinary text is never mistaken for a call.
    """
    decoder = json.JSONDecoder()
    start = text.find(JSON_OBJECT_START)
    while start != -1:
        try:
            candidate, _ = decoder.raw_decode(text, start)
        except json.JSONDecodeError:
            candidate = None
        tool_call = _as_tool_call(candidate, tool_names)
        if tool_call is not None:
            return tool_call
        start = text.find(JSON_OBJECT_START, start + 1)
    return None


def _as_tool_call(candidate: object, tool_names: Collection[str]) -> ToolCall | None:
    if not isinstance(candidate, dict):
        return None
    name = candidate.get("name")
    arguments = candidate.get("arguments")
    if not isinstance(name, str) or name not in tool_names or not isinstance(arguments, dict):
        return None
    return ToolCall(name=name, arguments=arguments)
