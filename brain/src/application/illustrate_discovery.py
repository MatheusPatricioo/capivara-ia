import logging
from typing import Protocol

from src.application.category_matcher import CategoryMatch
from src.application.chalkboard_artist import ChalkboardArtist, PinnedDrawing
from src.domain.discovery import Discovery
from src.domain.doodle import Doodle, DoodleLibrary, UnknownCategoryError
from src.domain.drawing import Drawing, DrawingStorageError, InvalidDrawingError
from src.domain.text_embedding import EmbeddingError

logger = logging.getLogger(__name__)


class CategoryFinder(Protocol):
    def closest(self, text: str) -> CategoryMatch: ...


class DrawingHand(Protocol):
    def redraw(self, reference: Doodle) -> Doodle: ...


class IllustrateDiscovery:
    """Sketches one element of a discovery she just saved, as a quick chalk doodle.

    The element is the doodle category closest in meaning to the discovery's title and
    summary (found with embeddings, no language model call). A real person's Quick, Draw!
    doodle of it is the reference, and her hand redraws it in her own way, so the drawing
    looks like what it is and still never comes out the same twice.
    When no category clearly stands out (a small margin over the runner-up), nothing in the
    discovery is drawable and the board is left as it is.
    """

    def __init__(
        self,
        category_finder: CategoryFinder,
        doodle_library: DoodleLibrary,
        hand: DrawingHand,
        artist: ChalkboardArtist,
        min_margin: float,
    ) -> None:
        self._category_finder = category_finder
        self._doodle_library = doodle_library
        self._hand = hand
        self._artist = artist
        self._min_margin = min_margin

    def illustrate(self, discovery: Discovery) -> PinnedDrawing | None:
        """Returns the pinned drawing, or None when nothing fits or drawing failed.

        A failure never undoes the saved discovery: it is only logged.
        """
        try:
            match = self._category_finder.closest(f"{discovery.title}. {discovery.summary}")
            if match.margin < self._min_margin:
                logger.info(
                    "No doodle fits '%s': closest was '%s' (%s)",
                    discovery.title,
                    match.category,
                    _scores(match),
                )
                return None
            logger.info(
                "Chose the doodle '%s' for '%s' (%s)",
                match.category,
                discovery.title,
                _scores(match),
            )
            doodle = self._hand.redraw(self._doodle_library.pick(match.category))
            drawing = Drawing(title=discovery.title, strokes=doodle.on_the_board())
            return self._artist.draw(drawing)
        except (
            EmbeddingError,
            UnknownCategoryError,
            InvalidDrawingError,
            DrawingStorageError,
        ) as error:
            logger.warning("Could not draw '%s': %s", discovery.title, error)
            return None


def _scores(match: CategoryMatch) -> str:
    return f"similarity {match.similarity:.3f}, margin {match.margin:.3f}"
