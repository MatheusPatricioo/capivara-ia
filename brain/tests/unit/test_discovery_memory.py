from datetime import date

import pytest

from src.domain.discovery import Discovery
from src.domain.discovery_memory import memory_text


@pytest.fixture
def moon_discovery() -> Discovery:
    return Discovery(
        title="Fases da lua",
        topic="astronomia",
        summary="A lua tem quatro fases.",
        sources=("https://example.com/lua",),
        discovered_on=date(2026, 11, 23),
    )


def test_memory_text_joins_title_topic_and_summary(moon_discovery: Discovery) -> None:
    assert memory_text(moon_discovery) == "Fases da lua\nastronomia\nA lua tem quatro fases."


def test_memory_text_leaves_the_sources_out(moon_discovery: Discovery) -> None:
    assert "https://" not in memory_text(moon_discovery)
