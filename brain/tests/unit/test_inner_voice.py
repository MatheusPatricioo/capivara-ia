import logging

import pytest

from src.application.inner_voice import InnerVoice
from src.domain.discovery import DiscoveryHeadline, DiscoveryStorageError

INVITATION = "(Você está sozinha. O que quer fazer?)"
MEMORY_TEMPLATE = "(Você já guardou:\n{discoveries}\nNão repita.)"
MAX_REMEMBERED_DISCOVERIES = 2
INNER_VOICE_LOGGER = "src.application.inner_voice"


class FakeCatalog:
    """Returns the given headlines and remembers the limit it was asked for."""

    def __init__(self, headlines: list[DiscoveryHeadline]) -> None:
        self.headlines = headlines
        self.requested_limits: list[int] = []

    def latest_headlines(self, limit: int) -> list[DiscoveryHeadline]:
        self.requested_limits.append(limit)
        return self.headlines[:limit]


class BrokenCatalog:
    def latest_headlines(self, limit: int) -> list[DiscoveryHeadline]:
        raise DiscoveryStorageError("disk unplugged")


def build_inner_voice(catalog: FakeCatalog | BrokenCatalog) -> InnerVoice:
    return InnerVoice(INVITATION, catalog, MEMORY_TEMPLATE, MAX_REMEMBERED_DISCOVERIES)


@pytest.fixture
def catalog_with_discoveries() -> FakeCatalog:
    return FakeCatalog(
        [
            DiscoveryHeadline(title="Peixes de rio", topic="animais"),
            DiscoveryHeadline(title="Estrelas gêmeas", topic=""),
        ]
    )


def test_lists_the_saved_discoveries_before_the_invitation(
    catalog_with_discoveries: FakeCatalog,
) -> None:
    composed = build_inner_voice(catalog_with_discoveries).compose()

    assert composed == (
        "(Você já guardou:\n"
        "- Peixes de rio (tema: animais)\n"
        "- Estrelas gêmeas\n"
        "Não repita.)\n\n"
        f"{INVITATION}"
    )


def test_asks_the_catalog_for_the_configured_number_of_discoveries(
    catalog_with_discoveries: FakeCatalog,
) -> None:
    build_inner_voice(catalog_with_discoveries).compose()

    assert catalog_with_discoveries.requested_limits == [MAX_REMEMBERED_DISCOVERIES]


def test_is_just_the_invitation_when_nothing_was_saved_yet() -> None:
    assert build_inner_voice(FakeCatalog([])).compose() == INVITATION


def test_is_just_the_invitation_when_the_discoveries_cannot_be_read() -> None:
    assert build_inner_voice(BrokenCatalog()).compose() == INVITATION


def test_logs_a_warning_when_the_discoveries_cannot_be_read(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.WARNING, logger=INNER_VOICE_LOGGER)

    build_inner_voice(BrokenCatalog()).compose()

    assert caplog.messages == ["Could not remember the saved discoveries: disk unplugged"]
