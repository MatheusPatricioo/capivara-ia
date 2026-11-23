import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from src.domain.body import Body, Place
from src.domain.chalkboard import Chalkboard
from src.domain.drawing import Drawing, DrawingRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PinnedDrawing:
    """A drawing that was saved as an image and pinned on the chalkboard."""

    drawing: Drawing
    file_name: str
    erased: Drawing | None
    """The old drawing erased to make room, if the board was full."""


class ChalkboardArtist:
    """Puts a finished drawing in the world: walks to the board, saves the image, pins it
    and shows it on the body.
    """

    def __init__(
        self,
        repository: DrawingRepository,
        chalkboard: Chalkboard,
        today: Callable[[], date] = date.today,
        body: Body | None = None,
    ) -> None:
        self._repository = repository
        self._chalkboard = chalkboard
        self._today = today
        self._body = body

    def draw(self, drawing: Drawing) -> PinnedDrawing:
        """Raises DrawingStorageError when the image cannot be saved; nothing is pinned then."""
        if self._body is not None:
            self._body.go_to(Place.CHALKBOARD)
        file_name = self._repository.save(drawing, self._today())
        erased = self._chalkboard.pin(drawing)
        if self._body is not None:
            self._body.show_chalkboard(self._chalkboard.drawings)
        logger.info("Drawing saved: %s (%d shape(s))", file_name, len(drawing.shapes))
        return PinnedDrawing(drawing=drawing, file_name=file_name, erased=erased)
