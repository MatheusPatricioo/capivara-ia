import logging
from datetime import date

import pytest

from src.application.drawing_artist import DrawingArtist, SavedDrawing
from src.domain.drawing import Drawing, DrawingStorageError, Point, Stroke

TODAY = date(2026, 11, 23)
SAVED_FILE_NAME = "2026-11-23-o-sol.png"
ARTIST_LOGGER = "src.application.drawing_artist"
SUN_DRAWING = Drawing(title="O Sol", strokes=(Stroke(points=(Point(160, 150), Point(240, 150))),))


class InMemoryDrawingRepository:
    def __init__(self) -> None:
        self.saved: list[tuple[Drawing, date]] = []

    def save(self, drawing: Drawing, drawn_on: date) -> str:
        self.saved.append((drawing, drawn_on))
        return SAVED_FILE_NAME


class FullDiskDrawingRepository:
    def save(self, drawing: Drawing, drawn_on: date) -> str:
        raise DrawingStorageError("no space left on device")


@pytest.fixture
def repository() -> InMemoryDrawingRepository:
    return InMemoryDrawingRepository()


@pytest.fixture
def artist(repository: InMemoryDrawingRepository) -> DrawingArtist:
    return DrawingArtist(repository, today=lambda: TODAY)


def test_saves_the_drawing_with_todays_date(
    artist: DrawingArtist, repository: InMemoryDrawingRepository
) -> None:
    artist.draw(SUN_DRAWING)

    assert repository.saved == [(SUN_DRAWING, TODAY)]


def test_returns_the_drawing_and_its_file(artist: DrawingArtist) -> None:
    assert artist.draw(SUN_DRAWING) == SavedDrawing(drawing=SUN_DRAWING, file_name=SAVED_FILE_NAME)


def test_fails_when_the_image_cannot_be_saved() -> None:
    artist = DrawingArtist(FullDiskDrawingRepository(), today=lambda: TODAY)

    with pytest.raises(DrawingStorageError):
        artist.draw(SUN_DRAWING)


def test_logs_the_saved_drawing(artist: DrawingArtist, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger=ARTIST_LOGGER)

    artist.draw(SUN_DRAWING)

    assert caplog.messages == [f"Drawing saved: {SAVED_FILE_NAME} (1 stroke(s))"]
