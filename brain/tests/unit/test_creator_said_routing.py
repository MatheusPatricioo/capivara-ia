import logging

import pytest

from src.domain.speech import VoiceMode
from src.infrastructure.world_event_router import WorldEventRouter
from src.infrastructure.world_messages import CreatorSaidMessage, NoticedMessage, VoiceModeMessage


@pytest.fixture
def router() -> WorldEventRouter:
    return WorldEventRouter(on_noticed=lambda event: None)


def test_hands_what_her_creator_said_to_the_registered_handler(router: WorldEventRouter) -> None:
    heard: list[str] = []
    router.when_creator_said(heard.append)

    router.route(CreatorSaidMessage(text="Oi, capivara!"))

    assert heard == ["Oi, capivara!"]


def test_warns_when_nobody_listens_to_her_creator(
    router: WorldEventRouter, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING):
        router.route(CreatorSaidMessage(text="Oi, capivara!"))

    assert "nobody is listening" in caplog.text


def test_other_events_do_not_reach_the_creator_handler(router: WorldEventRouter) -> None:
    heard: list[str] = []
    router.when_creator_said(heard.append)

    router.route(NoticedMessage(thing="pond", description="um lago"))

    assert heard == []


def test_hands_the_chosen_voice_mode_to_the_registered_handler(router: WorldEventRouter) -> None:
    chosen: list[VoiceMode] = []
    router.when_voice_mode_changed(chosen.append)

    router.route(VoiceModeMessage(mode=VoiceMode.MUTE))

    assert chosen == [VoiceMode.MUTE]


def test_warns_when_nobody_uses_the_voice_mode(
    router: WorldEventRouter, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING):
        router.route(VoiceModeMessage(mode=VoiceMode.MUTE))

    assert "nobody uses it" in caplog.text
