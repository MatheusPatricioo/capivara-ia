from datetime import date

from src.domain.discovery import Discovery
from src.domain.discovery_chunks import discovery_chunks

THREE_SENTENCES = "Elas nadam. Elas mergulham. Pássaros pousam nelas."


def a_discovery(summary: str) -> Discovery:
    return Discovery(
        title="Capivaras",
        topic="bichos",
        summary=summary,
        sources=("https://example.com",),
        discovered_on=date(2026, 11, 24),
    )


def test_a_short_summary_is_a_single_chunk_with_its_header() -> None:
    chunks = discovery_chunks(a_discovery("Elas nadam. Elas mergulham."))

    assert chunks == ["Capivaras\nbichos\nElas nadam. Elas mergulham."]


def test_a_long_summary_starts_with_the_whole_text() -> None:
    chunks = discovery_chunks(a_discovery(THREE_SENTENCES))

    assert chunks[0] == f"Capivaras\nbichos\n{THREE_SENTENCES}"


def test_a_long_summary_adds_overlapping_windows_of_two_sentences() -> None:
    chunks = discovery_chunks(a_discovery(THREE_SENTENCES))

    assert chunks[1:] == [
        "Capivaras\nbichos\nElas nadam. Elas mergulham.",
        "Capivaras\nbichos\nElas mergulham. Pássaros pousam nelas.",
    ]


def test_question_and_exclamation_marks_also_end_sentences() -> None:
    chunks = discovery_chunks(a_discovery("Sabia? Elas nadam! E mergulham."))

    assert len(chunks) == 3
