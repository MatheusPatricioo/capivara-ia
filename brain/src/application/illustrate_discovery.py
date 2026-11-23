import logging

from src.application.chalkboard_artist import ChalkboardArtist, PinnedDrawing
from src.application.drawing_schema import DRAWING_DECISION_SCHEMA, MAX_SUGGESTED_SHAPES
from src.application.tools.shape_arguments import parse_shapes
from src.domain.discovery import Discovery
from src.domain.drawing import (
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    Drawing,
    DrawingStorageError,
    InvalidDrawingError,
)
from src.domain.language_model import (
    ChatMessage,
    LanguageModelError,
    Role,
    StructuredLanguageModel,
)
from src.domain.tool import ToolError

logger = logging.getLogger(__name__)


class IllustrateDiscovery:
    """Offers the capybara a drawing for a discovery she just saved, and draws it if she wants.

    A short, separate call in structured output instead of hoping she calls the draw tool:
    she always gets asked, the answer always comes in a valid shape, and only the discovery
    is sent (a few hundred tokens), not the whole conversation.
    """

    def __init__(
        self,
        language_model: StructuredLanguageModel,
        artist: ChalkboardArtist,
        instructions_template: str,
    ) -> None:
        self._language_model = language_model
        self._artist = artist
        self._instructions = (
            instructions_template.replace("{max_shapes}", str(MAX_SUGGESTED_SHAPES))
            .replace("{width}", str(CANVAS_WIDTH))
            .replace("{height}", str(CANVAS_HEIGHT))
        )

    def illustrate(self, discovery: Discovery) -> PinnedDrawing | None:
        """Returns the pinned drawing, or None when she chose not to draw or drawing failed.

        A failure never undoes the saved discovery: it is only logged.
        """
        try:
            reply = self._language_model.complete_json(
                self._messages(discovery), DRAWING_DECISION_SCHEMA
            )
            if reply.data.get("wants_to_draw") is not True:
                logger.info("Chose not to draw: %s", discovery.title)
                return None
            drawing = Drawing(title=discovery.title, shapes=parse_shapes(reply.data.get("shapes")))
            return self._artist.draw(drawing)
        except (LanguageModelError, ToolError, InvalidDrawingError, DrawingStorageError) as error:
            logger.warning("Could not draw '%s': %s", discovery.title, error)
            return None

    def _messages(self, discovery: Discovery) -> list[ChatMessage]:
        saved_discovery = (
            f"Título: {discovery.title}\nTema: {discovery.topic}\nResumo: {discovery.summary}"
        )
        return [
            ChatMessage(Role.SYSTEM, self._instructions),
            ChatMessage(Role.USER, saved_discovery),
        ]
