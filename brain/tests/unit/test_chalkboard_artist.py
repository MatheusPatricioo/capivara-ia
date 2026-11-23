import logging
from datetime import date

import pytest

from src.application.chalkboard_artist import ChalkboardArtist, PinnedDrawing
from src.domain.body import Place
from src.domain.chalkboard import Chalkboard
from src.domain.drawing import Drawing, DrawingStorageError, Point, Stroke

TODAY = date(2026, 11, 23)
SAVED_FILE_NAME = "2026-11-23-o-sol.png"
ARTIST_LOGGER = "src.application.chalkboard_artist"
SUN_DRAWING = Drawing(title="O Sol", strokes=(Stroke(points=(Point(160, 150), Point(240, 150))),))
MOON_DRAWING = Drawing(title="A Lua", strokes=(Stroke(points=(Point(100, 100), Point(130, 130))),))


class InMemoryDrawingRepository:
    def __init__(self) -> None:
        self.saved: list[tuple[Drawing, date]] = []

    def save(self, drawing: Drawing, drawn_on: date) -> str:
        self.saved.append((drawing, drawn_on))
        return SAVED_FILE_NAME


class FullDiskDrawingRepository:
    def save(self, drawing: Drawing, drawn_on: date) -> str:
        raise DrawingStorageError("no space left on device")


class RecordingBody:
    def __init__(self) -> None:
        self.shown_chalkboards: list[tuple[Drawing, ...]] = []
        self.visited_places: list[Place] = []

    def go_to(self, place: Place) -> None:
        self.visited_places.append(place)

    def show_chalkboard(self, drawings: tuple[Drawing, ...]) -> None:
        self.shown_chalkboards.append(drawings)


@pytest.fixture
def repository() -> InMemoryDrawingRepository:
    return InMemoryDrawingRepository()


@pytest.fixture
def chalkboard() -> Chalkboard:
    return Chalkboard(capacity=1)


@pytest.fixture
def body() -> RecordingBody:
    return RecordingBody()


@pytest.fixture
def artist(
    repository: InMemoryDrawingRepository, chalkboard: Chalkboard, body: RecordingBody
) -> ChalkboardArtist:
    return ChalkboardArtist(repository, chalkboard, today=lambda: TODAY, body=body)


def test_saves_the_drawing_with_todays_date(
    artist: ChalkboardArtist, repository: InMemoryDrawingRepository
) -> None:
    artist.draw(SUN_DRAWING)

    assert repository.saved == [(SUN_DRAWING, TODAY)]


def test_pins_the_drawing_on_the_chalkboard(
    artist: ChalkboardArtist, chalkboard: Chalkboard
) -> None:
    artist.draw(SUN_DRAWING)

    assert chalkboard.drawings == (SUN_DRAWING,)


def test_shows_the_updated_chalkboard_on_the_body(
    artist: ChalkboardArtist, body: RecordingBody
) -> None:
    artist.draw(SUN_DRAWING)

    assert body.shown_chalkboards == [(SUN_DRAWING,)]


def test_returns_the_pinned_drawing_and_its_file(artist: ChalkboardArtist) -> None:
    assert artist.draw(SUN_DRAWING) == PinnedDrawing(
        drawing=SUN_DRAWING, file_name=SAVED_FILE_NAME, erased=None
    )


def test_returns_the_drawing_erased_to_make_room(artist: ChalkboardArtist) -> None:
    artist.draw(SUN_DRAWING)

    assert artist.draw(MOON_DRAWING).erased == SUN_DRAWING


def test_pins_nothing_when_the_image_cannot_be_saved(chalkboard: Chalkboard) -> None:
    artist = ChalkboardArtist(FullDiskDrawingRepository(), chalkboard, today=lambda: TODAY)

    with pytest.raises(DrawingStorageError):
        artist.draw(SUN_DRAWING)

    assert chalkboard.drawings == ()


def test_logs_the_saved_drawing(artist: ChalkboardArtist, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger=ARTIST_LOGGER)

    artist.draw(SUN_DRAWING)

    assert caplog.messages == [f"Drawing saved: {SAVED_FILE_NAME} (1 stroke(s))"]


def test_walks_to_the_chalkboard_before_drawing(
    artist: ChalkboardArtist, body: RecordingBody
) -> None:
    artist.draw(SUN_DRAWING)

    assert body.visited_places == [Place.CHALKBOARD]
