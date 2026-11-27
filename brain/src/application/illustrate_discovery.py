import logging
from typing import Protocol

from src.application.drawing_artist import DrawingArtist, SavedDrawing
from src.domain.discovery import Discovery
from src.domain.doodle import Doodle, DoodleLibrary, UnknownCategoryError
from src.domain.drawing import Drawing, DrawingStorageError, InvalidDrawingError
from src.domain.language_model import LanguageModelError
from src.domain.text_embedding import EmbeddingError

logger = logging.getLogger(__name__)


class CategoryChooser(Protocol):
    def choose(self, discovery: Discovery) -> str | None: ...


class DrawingHand(Protocol):
    def redraw(self, reference: Doodle) -> Doodle: ...


class IllustrateDiscovery:
    """Sketches one element of a discovery she just saved, as a quick doodle.

    The chooser picks what to sketch (or nothing, when nothing in the discovery is
    drawable). A real person's Quick, Draw! doodle of it is the reference, and her hand
    redraws it in her own way, so the drawing looks like what it is and still never comes
    out the same twice.
    """

    def __init__(
        self,
        category_chooser: CategoryChooser,
        doodle_library: DoodleLibrary,
        hand: DrawingHand,
        artist: DrawingArtist,
    ) -> None:
        self._category_chooser = category_chooser
        self._doodle_library = doodle_library
        self._hand = hand
        self._artist = artist

    def illustrate(self, discovery: Discovery) -> SavedDrawing | None:
        """Returns the saved drawing, or None when nothing fits or drawing failed.

        A failure never undoes the saved discovery: it is only logged.
        """
        try:
            category = self._category_chooser.choose(discovery)
            if category is None:
                logger.info("Nothing to sketch for: %s", discovery.title)
                return None
            doodle = self._hand.redraw(self._doodle_library.pick(category))
            drawing = Drawing(title=discovery.title, strokes=doodle.on_the_board())
            return self._artist.draw(drawing)
        except (
            EmbeddingError,
            LanguageModelError,
            UnknownCategoryError,
            InvalidDrawingError,
            DrawingStorageError,
        ) as error:
            logger.warning("Could not draw '%s': %s", discovery.title, error)
            return None
