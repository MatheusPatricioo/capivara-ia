import logging
from datetime import date

import pytest

from src.application.chalkboard_artist import ChalkboardArtist, PinnedDrawing
from src.application.illustrate_discovery import IllustrateDiscovery
from src.domain.chalkboard import Chalkboard
from src.domain.discovery import Discovery
from src.domain.doodle import Doodle, DoodleLibrary
from src.domain.drawing import Drawing, DrawingStorageError
from src.domain.language_model import LanguageModelError
from src.domain.text_embedding import EmbeddingError

TODAY = date(2026, 11, 23)
SAVED_FILE_NAME = "2026-11-23-o-sol.png"
ILLUSTRATE_LOGGER = "src.application.illustrate_discovery"
SUN_DOODLE = Doodle(category="sun", strokes=(((0, 128), (255, 128)),))
SUN_IN_HER_HAND = Doodle(category="sun", strokes=(((0, 120), (255, 140)),))
DOODLE_LIBRARY = DoodleLibrary({"sun": [SUN_DOODLE]})
SUN_DISCOVERY = Discovery(
    title="O Sol",
    topic="estrelas",
    summary="O Sol é uma estrela gigante.",
    sources=("https://example.com/sol",),
    discovered_on=TODAY,
)
SUN_DRAWING = Drawing(title="O Sol", strokes=SUN_IN_HER_HAND.on_the_board())


class FixedChooser:
    """Always chooses the same category (None: nothing to sketch)."""

    def __init__(self, category: str | None) -> None:
        self._category = category

    def choose(self, discovery: Discovery) -> str | None:
        return self._category


class FailingChooser:
    def __init__(self, error: Exception) -> None:
        self._error = error

    def choose(self, discovery: Discovery) -> str | None:
        raise self._error


class RecordingHand:
    """Redraws every reference as SUN_IN_HER_HAND and remembers the references."""

    def __init__(self) -> None:
        self.references: list[Doodle] = []

    def redraw(self, reference: Doodle) -> Doodle:
        self.references.append(reference)
        return SUN_IN_HER_HAND


class InMemoryDrawingRepository:
    def __init__(self) -> None:
        self.saved: list[Drawing] = []

    def save(self, drawing: Drawing, drawn_on: date) -> str:
        self.saved.append(drawing)
        return SAVED_FILE_NAME


class FullDiskDrawingRepository:
    def save(self, drawing: Drawing, drawn_on: date) -> str:
        raise DrawingStorageError("no space left on device")


@pytest.fixture
def repository() -> InMemoryDrawingRepository:
    return InMemoryDrawingRepository()


@pytest.fixture
def artist(repository: InMemoryDrawingRepository) -> ChalkboardArtist:
    return ChalkboardArtist(repository, Chalkboard(capacity=3), today=lambda: TODAY)


@pytest.fixture
def hand() -> RecordingHand:
    return RecordingHand()


@pytest.fixture
def illustrator(hand: RecordingHand, artist: ChalkboardArtist) -> IllustrateDiscovery:
    return IllustrateDiscovery(FixedChooser("sun"), DOODLE_LIBRARY, hand, artist)


def illustrator_choosing(
    chooser: FixedChooser | FailingChooser, artist: ChalkboardArtist
) -> IllustrateDiscovery:
    return IllustrateDiscovery(chooser, DOODLE_LIBRARY, RecordingHand(), artist)


def test_her_hand_redraws_a_doodle_of_the_chosen_category(
    illustrator: IllustrateDiscovery, hand: RecordingHand
) -> None:
    illustrator.illustrate(SUN_DISCOVERY)

    assert hand.references == [SUN_DOODLE]


def test_draws_what_her_hand_redrew(
    illustrator: IllustrateDiscovery, repository: InMemoryDrawingRepository
) -> None:
    illustrator.illustrate(SUN_DISCOVERY)

    assert repository.saved == [SUN_DRAWING]


def test_returns_the_pinned_drawing(illustrator: IllustrateDiscovery) -> None:
    assert illustrator.illustrate(SUN_DISCOVERY) == PinnedDrawing(
        drawing=SUN_DRAWING, file_name=SAVED_FILE_NAME, erased=None
    )


def test_draws_nothing_when_there_is_nothing_to_sketch(
    artist: ChalkboardArtist, repository: InMemoryDrawingRepository
) -> None:
    result = illustrator_choosing(FixedChooser(None), artist).illustrate(SUN_DISCOVERY)

    assert (result, repository.saved) == (None, [])


def test_draws_nothing_for_a_category_without_doodles(
    artist: ChalkboardArtist, repository: InMemoryDrawingRepository
) -> None:
    result = illustrator_choosing(FixedChooser("volcano"), artist).illustrate(SUN_DISCOVERY)

    assert (result, repository.saved) == (None, [])


def test_returns_none_when_the_embedding_model_is_offline(artist: ChalkboardArtist) -> None:
    illustrator = illustrator_choosing(FailingChooser(EmbeddingError("refused")), artist)

    assert illustrator.illustrate(SUN_DISCOVERY) is None


def test_returns_none_when_the_language_model_is_offline(artist: ChalkboardArtist) -> None:
    illustrator = illustrator_choosing(FailingChooser(LanguageModelError("refused")), artist)

    assert illustrator.illustrate(SUN_DISCOVERY) is None


def test_returns_none_when_the_image_cannot_be_saved() -> None:
    artist = ChalkboardArtist(FullDiskDrawingRepository(), Chalkboard(capacity=3))

    assert illustrator_choosing(FixedChooser("sun"), artist).illustrate(SUN_DISCOVERY) is None


def test_logs_when_there_is_nothing_to_sketch(
    artist: ChalkboardArtist, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger=ILLUSTRATE_LOGGER)

    illustrator_choosing(FixedChooser(None), artist).illustrate(SUN_DISCOVERY)

    assert caplog.messages == ["Nothing to sketch for: O Sol"]


def test_logs_why_the_drawing_failed(
    artist: ChalkboardArtist, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.WARNING, logger=ILLUSTRATE_LOGGER)
    illustrator = illustrator_choosing(FailingChooser(EmbeddingError("connection refused")), artist)

    illustrator.illustrate(SUN_DISCOVERY)

    assert caplog.messages == ["Could not draw 'O Sol': connection refused"]
