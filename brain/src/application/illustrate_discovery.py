import logging

from src.application.chalkboard_artist import ChalkboardArtist, PinnedDrawing
from src.application.drawing_schema import drawing_decision_schema
from src.domain.discovery import Discovery
from src.domain.drawing import Drawing, DrawingStorageError, InvalidDrawingError
from src.domain.language_model import (
    ChatMessage,
    LanguageModelError,
    Role,
    StructuredLanguageModel,
)
from src.domain.sketch import SketchBook, UnknownSketchError

logger = logging.getLogger(__name__)

SKETCHES_PLACEHOLDER = "{sketches}"


class IllustrateDiscovery:
    """Offers the capybara a drawing for a discovery she just saved, and draws it if she wants.

    A short, separate call in structured output instead of hoping she calls the draw tool:
    she always gets asked, the answer always comes in a valid shape, and only the discovery
    is sent (a few hundred tokens), not the whole conversation. She picks one sketch from
    her sketch book; the sketch is then drawn big in the middle of the board.
    """

    def __init__(
        self,
        language_model: StructuredLanguageModel,
        artist: ChalkboardArtist,
        instructions_template: str,
        sketch_book: SketchBook,
    ) -> None:
        self._language_model = language_model
        self._artist = artist
        self._sketch_book = sketch_book
        self._schema = drawing_decision_schema(sketch_book.names)
        self._instructions = instructions_template.replace(
            SKETCHES_PLACEHOLDER, self._sketch_list()
        )

    def illustrate(self, discovery: Discovery) -> PinnedDrawing | None:
        """Returns the pinned drawing, or None when she chose not to draw or drawing failed.

        A failure never undoes the saved discovery: it is only logged.
        """
        try:
            reply = self._language_model.complete_json(self._messages(discovery), self._schema)
            if reply.data.get("wants_to_draw") is not True:
                logger.info("Chose not to draw: %s", discovery.title)
                return None
            sketch = self._sketch_book.find(str(reply.data.get("sketch")))
            logger.info("Chose the sketch '%s' for: %s", sketch.name, discovery.title)
            drawing = Drawing(title=discovery.title, strokes=sketch.on_the_board())
            return self._artist.draw(drawing)
        except (
            LanguageModelError,
            UnknownSketchError,
            InvalidDrawingError,
            DrawingStorageError,
        ) as error:
            logger.warning("Could not draw '%s': %s", discovery.title, error)
            return None

    def _sketch_list(self) -> str:
        return "\n".join(
            f"- {sketch.name}: {sketch.description}" for sketch in self._sketch_book.sketches
        )

    def _messages(self, discovery: Discovery) -> list[ChatMessage]:
        saved_discovery = (
            f"Título: {discovery.title}\nTema: {discovery.topic}\nResumo: {discovery.summary}"
        )
        return [
            ChatMessage(Role.SYSTEM, self._instructions),
            ChatMessage(Role.USER, saved_discovery),
        ]
