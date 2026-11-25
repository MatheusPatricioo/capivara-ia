import logging

import pytest

from src.infrastructure.world_event_router import WorldEventRouter
from src.infrastructure.world_messages import CreatorSaidMessage, NoticedMessage


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
