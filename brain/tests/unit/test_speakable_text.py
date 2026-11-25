import pytest

from src.domain.speakable_text import speakable_text


def test_plain_text_is_said_as_written() -> None:
    assert speakable_text("Oi, criador! Tudo bem?") == "Oi, criador! Tudo bem?"


@pytest.mark.parametrize(
    ("written_text", "expected_speech"),
    [
        ("Eu **amo** água!", "Eu amo água!"),
        ("Que *bonito*.", "Que bonito."),
        ("Achei o `save_discovery`.", "Achei o save discovery."),
        ("Foi _incrível_!", "Foi incrível!"),
        ("Isso é ~~chato~~ legal.", "Isso é chato legal."),
    ],
)
def test_emphasis_marks_are_not_said(written_text: str, expected_speech: str) -> None:
    assert speakable_text(written_text) == expected_speech


def test_a_markdown_link_keeps_only_its_text() -> None:
    written_text = "Li na [Wikipédia](https://pt.wikipedia.org/wiki/Capivara) hoje."

    assert speakable_text(written_text) == "Li na Wikipédia hoje."


def test_a_bare_web_address_is_left_out() -> None:
    written_text = "Olha isso https://exemplo.com/capivaras e me conta."

    assert speakable_text(written_text) == "Olha isso e me conta."


def test_emojis_are_left_out() -> None:
    assert speakable_text("Bom dia! 🌞🦫 Vamos pesquisar? ❤️") == "Bom dia! Vamos pesquisar?"


def test_list_markers_are_dropped_and_lines_join_into_one_speech() -> None:
    written_text = "## Descobertas\n- Capivaras nadam.\n2. Elas comem capim."

    assert speakable_text(written_text) == "Descobertas Capivaras nadam. Elas comem capim."


def test_a_reply_made_only_of_symbols_has_nothing_to_say() -> None:
    assert speakable_text("🦫✨ https://exemplo.com") == ""
