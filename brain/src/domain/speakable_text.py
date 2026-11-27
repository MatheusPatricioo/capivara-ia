import re

MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")
"""[text](address): only the text is said."""
WEB_ADDRESS = re.compile(r"(?:https?://|www\.)\S+")
LINE_MARKER = re.compile(r"^\s*(?:#{1,6}|[-*+>]|\d+[.)])\s+", re.MULTILINE)
"""Headings, bullets, quotes and numbered items at the start of a line."""
EMPHASIS_MARK = re.compile(r"[*`~]+")
UNDERSCORE = re.compile(r"_+")
"""Underlines _like this_ and names like save_discovery: said as a space."""
EMOJI = re.compile(
    "["
    "\U0001f1e6-\U0001f1ff"  # flags
    "\U0001f300-\U0001faff"  # pictographs, faces, animals, food...
    "\u2600-\u27bf"  # weather, hearts, stars, check marks
    "\ufe0f\u200d"  # emoji variation selector and the joiner that glues emojis together
    "]+"
)
SPACE_BEFORE_PUNCTUATION = re.compile(r"\s+([,.!?;:])")
WHITESPACE = re.compile(r"\s+")
# A tool call the model wrote as text instead of calling it, like "Save_discovery:" and
# the "- Título: ..." lines under it: never said or shown, it is not part of her talk.
TOOL_WRITTEN_AS_TEXT = re.compile(
    r"^[ \t]*[*`#]*[ \t]*(?:save_discovery|suggest_improvement|web_search|recall_memory)\b.*"
    r"(?:\n[ \t]*(?:[-*\u2022]|[\w\u00C0-\u00FF ]{1,20}:).*)*",
    re.IGNORECASE | re.MULTILINE,
)


def speakable_text(written_text: str) -> str:
    """Her written reply as it should be said out loud. A synthesizer reads every symbol,
    so markdown marks, emojis and web addresses would come out as noise ("asterisco",
    "agá tê tê pê"), and a tool written as text is not talk at all. Line breaks become
    spaces: the punctuation already gives the pauses."""
    text = TOOL_WRITTEN_AS_TEXT.sub("", written_text)
    text = MARKDOWN_LINK.sub(r"\1", text)
    text = WEB_ADDRESS.sub("", text)
    text = LINE_MARKER.sub("", text)
    text = EMPHASIS_MARK.sub("", text)
    text = UNDERSCORE.sub(" ", text)
    text = EMOJI.sub("", text)
    text = WHITESPACE.sub(" ", text)
    return SPACE_BEFORE_PUNCTUATION.sub(r"\1", text).strip()
