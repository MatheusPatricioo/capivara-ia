from dataclasses import replace
from datetime import date

import pytest

from src.application.tools.conversation_discoveries import ConversationDiscoveries
from src.domain.discovery import Discovery

DISCOVERY = Discovery(
    title="Vaga-lumes",
    topic="insetos",
    summary="Eles piscam para conversar!",
    sources=("https://example.com/fireflies",),
    discovered_on=date(2026, 11, 24),
)


@pytest.fixture
def saved_discoveries() -> ConversationDiscoveries:
    return ConversationDiscoveries()


def test_has_no_latest_discovery_before_anything_is_saved(
    saved_discoveries: ConversationDiscoveries,
) -> None:
    assert saved_discoveries.latest is None


def test_latest_is_the_last_discovery_remembered(
    saved_discoveries: ConversationDiscoveries,
) -> None:
    newest = replace(DISCOVERY, title="Vitórias-régias")
    saved_discoveries.remember(DISCOVERY)
    saved_discoveries.remember(newest)

    assert saved_discoveries.latest == newest
