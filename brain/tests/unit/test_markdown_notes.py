from src.infrastructure.markdown_notes import first_value_after, section_lines

LINES = [
    "# Vaga-lumes",
    "",
    "- **Data:** 2026-11-24",
    "",
    "## O que eu descobri",
    "",
    "Eles piscam.",
    "",
    "## Fontes",
    "",
    "- https://example.com",
]


def test_first_value_after_returns_what_follows_the_prefix() -> None:
    assert first_value_after("- **Data:** ", LINES) == "2026-11-24"


def test_first_value_after_is_empty_when_no_line_has_the_prefix() -> None:
    assert first_value_after("- **Tema:** ", LINES) == ""


def test_section_lines_stop_at_the_next_heading() -> None:
    assert section_lines("## O que eu descobri", LINES) == ["", "Eles piscam.", ""]


def test_section_lines_are_empty_when_the_heading_is_missing() -> None:
    assert section_lines("## Por que eu quero", LINES) == []
