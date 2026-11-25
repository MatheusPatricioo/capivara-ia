import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from src.domain.drawing import Drawing, DrawingRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SavedDrawing:
    """A drawing saved as an image in the discoveries folder."""

    drawing: Drawing
    file_name: str


class DrawingArtist:
    """Saves a finished drawing as an image. She draws at the computer, where she already
    is after saving the discovery, so she does not walk anywhere else.
    """

    def __init__(
        self, repository: DrawingRepository, today: Callable[[], date] = date.today
    ) -> None:
        self._repository = repository
        self._today = today

    def draw(self, drawing: Drawing) -> SavedDrawing:
        """Raises DrawingStorageError when the image cannot be saved."""
        file_name = self._repository.save(drawing, self._today())
        logger.info("Drawing saved: %s (%d stroke(s))", file_name, len(drawing.strokes))
        return SavedDrawing(drawing=drawing, file_name=file_name)
