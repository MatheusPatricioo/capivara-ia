import logging
from datetime import date

import pytest

from src.application.category_matcher import CategoryMatch
from src.application.chalkboard_artist import ChalkboardArtist, PinnedDrawing
from src.application.illustrate_discovery import IllustrateDiscovery
from src.domain.chalkboard import Chalkboard
from src.domain.discovery import Discovery
from src.domain.doodle import Doodle, DoodleLibrary
from src.domain.drawing import Drawing, DrawingStorageError
from src.domain.text_embedding import EmbeddingError

TODAY = date(2026, 11, 23)
SAVED_FILE_NAME = "2026-11-23-o-sol.png"
ILLUSTRATE_LOGGER = "src.application.illustrate_discovery"
MIN_MARGIN = 0.02
SUN_DOODLE = Doodle(category="sun", strokes=(((0, 128), (255, 128)),))
DOODLE_LIBRARY = DoodleLibrary({"sun": [SUN_DOODLE]})
SUN_DISCOVERY = Discovery(
    title="O Sol",
    topic="estrelas",
    summary="O Sol é uma estrela gigante.",
    sources=("https://example.com/sol",),
    discovered_on=TODAY,
)
SUN_IN_HER_HAND = Doodle(category="sun", strokes=(((0, 120), (255, 140)),))
SUN_DRAWING = Drawing(title="O Sol", strokes=SUN_IN_HER_HAND.on_the_board())
CLEARLY_THE_SUN = CategoryMatch(category="sun", similarity=0.81, margin=0.12)
TORN_ABOUT_THE_SUN = CategoryMatch(category="sun", similarity=0.61, margin=0.005)
A_CATEGORY_WITHOUT_DOODLES = CategoryMatch(category="volcano", similarity=0.8, margin=0.1)


class ScriptedCategoryFinder:
    """Always finds the same match and records the texts it was given."""

    def __init__(self, match: CategoryMatch) -> None:
        self._match = match
        self.received_texts: list[str] = []

    def closest(self, text: str) -> CategoryMatch:
        self.received_texts.append(text)
        return self._match


class RecordingHand:
    """Redraws every reference as SUN_IN_HER_HAND and remembers the references."""

    def __init__(self) -> None:
        self.references: list[Doodle] = []

    def redraw(self, reference: Doodle) -> Doodle:
        self.references.append(reference)
        return SUN_IN_HER_HAND


class OfflineCategoryFinder:
    def closest(self, text: str) -> CategoryMatch:
        raise EmbeddingError("connection refused")


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
def finder_sure_of_the_sun() -> ScriptedCategoryFinder:
    return ScriptedCategoryFinder(CLEARLY_THE_SUN)


@pytest.fixture
def illustrator(
    finder_sure_of_the_sun: ScriptedCategoryFinder, hand: RecordingHand, artist: ChalkboardArtist
) -> IllustrateDiscovery:
    return IllustrateDiscovery(finder_sure_of_the_sun, DOODLE_LIBRARY, hand, artist, MIN_MARGIN)


def illustrator_finding(match: CategoryMatch, artist: ChalkboardArtist) -> IllustrateDiscovery:
    return IllustrateDiscovery(
        ScriptedCategoryFinder(match), DOODLE_LIBRARY, RecordingHand(), artist, MIN_MARGIN
    )


def test_her_hand_redraws_a_doodle_of_the_closest_category(
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


def test_looks_for_the_category_by_the_title_and_the_summary(
    illustrator: IllustrateDiscovery, finder_sure_of_the_sun: ScriptedCategoryFinder
) -> None:
    illustrator.illustrate(SUN_DISCOVERY)

    assert finder_sure_of_the_sun.received_texts == ["O Sol. O Sol é uma estrela gigante."]


def test_draws_nothing_when_no_category_stands_out(
    artist: ChalkboardArtist, repository: InMemoryDrawingRepository
) -> None:
    result = illustrator_finding(TORN_ABOUT_THE_SUN, artist).illustrate(SUN_DISCOVERY)

    assert (result, repository.saved) == (None, [])


def test_draws_when_the_margin_is_exactly_the_minimum(
    artist: ChalkboardArtist, repository: InMemoryDrawingRepository
) -> None:
    just_enough = CategoryMatch(category="sun", similarity=0.7, margin=MIN_MARGIN)

    illustrator_finding(just_enough, artist).illustrate(SUN_DISCOVERY)

    assert repository.saved == [SUN_DRAWING]


def test_draws_nothing_for_a_category_without_doodles(
    artist: ChalkboardArtist, repository: InMemoryDrawingRepository
) -> None:
    result = illustrator_finding(A_CATEGORY_WITHOUT_DOODLES, artist).illustrate(SUN_DISCOVERY)

    assert (result, repository.saved) == (None, [])


def test_returns_none_when_the_embedding_model_is_offline(artist: ChalkboardArtist) -> None:
    illustrator = IllustrateDiscovery(
        OfflineCategoryFinder(), DOODLE_LIBRARY, RecordingHand(), artist, MIN_MARGIN
    )

    assert illustrator.illustrate(SUN_DISCOVERY) is None


def test_returns_none_when_the_image_cannot_be_saved() -> None:
    artist = ChalkboardArtist(FullDiskDrawingRepository(), Chalkboard(capacity=3))

    assert illustrator_finding(CLEARLY_THE_SUN, artist).illustrate(SUN_DISCOVERY) is None


def test_logs_the_chosen_category_and_its_scores(
    illustrator: IllustrateDiscovery, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger=ILLUSTRATE_LOGGER)

    illustrator.illustrate(SUN_DISCOVERY)

    assert caplog.messages == [
        "Chose the doodle 'sun' for 'O Sol' (similarity 0.810, margin 0.120)"
    ]


def test_logs_the_closest_category_when_nothing_fits(
    artist: ChalkboardArtist, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger=ILLUSTRATE_LOGGER)

    illustrator_finding(TORN_ABOUT_THE_SUN, artist).illustrate(SUN_DISCOVERY)

    assert caplog.messages == [
        "No doodle fits 'O Sol': closest was 'sun' (similarity 0.610, margin 0.005)"
    ]


def test_logs_why_the_drawing_failed(
    artist: ChalkboardArtist, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.WARNING, logger=ILLUSTRATE_LOGGER)
    illustrator = IllustrateDiscovery(
        OfflineCategoryFinder(), DOODLE_LIBRARY, RecordingHand(), artist, MIN_MARGIN
    )

    illustrator.illustrate(SUN_DISCOVERY)

    assert caplog.messages == ["Could not draw 'O Sol': connection refused"]
