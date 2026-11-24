"""Reading back the simple Markdown notes the capybara writes (discoveries, suggestions).

Her notes are always "- **Label:** value" lines and "## Heading" sections, so these two
helpers are all the parsing they need. Shared so every repository reads the same way.
"""

SECTION_PREFIX = "## "


def first_value_after(prefix: str, lines: list[str]) -> str:
    """Returns what follows the prefix on the first line that starts with it, or ''."""
    for line in lines:
        if line.startswith(prefix):
            return line.removeprefix(prefix).strip()
    return ""


def section_lines(heading: str, lines: list[str]) -> list[str]:
    """The lines under a "## " heading, up to the next "## " heading (empty when missing)."""
    if heading not in lines:
        return []
    section: list[str] = []
    for line in lines[lines.index(heading) + 1 :]:
        if line.startswith(SECTION_PREFIX):
            break
        section.append(line)
    return section
