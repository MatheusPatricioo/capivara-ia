import logging
from datetime import date

import pytest

from src.application.chalkboard_artist import ChalkboardArtist, PinnedDrawing
from src.application.drawing_schema import DRAWING_DECISION_SCHEMA
from src.application.illustrate_discovery import IllustrateDiscovery
from src.domain.chalkboard import Chalkboard
from src.domain.discovery import Discovery
from src.domain.drawing import Drawing, DrawingStorageError, Point, Stroke
from src.domain.language_model import (
    ChatMessage,
    LanguageModelError,
    Role,
    StructuredReply,
)

TODAY = date(2026, 11, 23)
SAVED_FILE_NAME = "2026-11-23-o-sol.png"
ILLUSTRATE_LOGGER = "src.application.illustrate_discovery"
INSTRUCTIONS_TEMPLATE = "Lousa {width}x{height}, até {max_strokes} traços de {max_points} pontos."
SUN_DISCOVERY = Discovery(
    title="O Sol",
    topic="estrelas",
    summary="O Sol é uma estrela gigante.",
    sources=("https://example.com/sol",),
    discovered_on=TODAY,
)
SUN_STROKE = [[160, 150], [240, 150]]
SUN_DRAWING = Drawing(title="O Sol", strokes=(Stroke(points=(Point(160, 150), Point(240, 150))),))
WANTS_TO_DRAW_THE_SUN = StructuredReply(data={"wants_to_draw": True, "strokes": [SUN_STROKE]})
DOES_NOT_WANT_TO_DRAW = StructuredReply(data={"wants_to_draw": False, "strokes": []})
STROKE_OUTSIDE_THE_BOARD = StructuredReply(
    data={"wants_to_draw": True, "strokes": [[[999, 0], [10, 10]]]}
)
STROKE_WITHOUT_POINTS = StructuredReply(
    data={"wants_to_draw": True, "strokes": [{"type": "text", "text": "Sol"}]}
)


class ScriptedStructuredLanguageModel:
    """Always gives the same structured reply and records what it was asked."""

    def __init__(self, reply: StructuredReply) -> None:
        self._reply = reply
        self.received_messages: list[list[ChatMessage]] = []
        self.received_schemas: list[dict[str, object]] = []

    def complete_json(
        self, messages: list[ChatMessage], schema: dict[str, object]
    ) -> StructuredReply:
        self.received_messages.append(messages)
        self.received_schemas.append(schema)
        return self._reply


class UnreachableStructuredLanguageModel:
    def complete_json(
        self, messages: list[ChatMessage], schema: dict[str, object]
    ) -> StructuredReply:
        raise LanguageModelError("connection refused")


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


def illustrator_answering(reply: StructuredReply, artist: ChalkboardArtist) -> IllustrateDiscovery:
    return IllustrateDiscovery(
        ScriptedStructuredLanguageModel(reply), artist, INSTRUCTIONS_TEMPLATE
    )


@pytest.fixture
def language_model_wanting_to_draw() -> ScriptedStructuredLanguageModel:
    return ScriptedStructuredLanguageModel(WANTS_TO_DRAW_THE_SUN)


@pytest.fixture
def illustrator_wanting_to_draw(
    language_model_wanting_to_draw: ScriptedStructuredLanguageModel, artist: ChalkboardArtist
) -> IllustrateDiscovery:
    return IllustrateDiscovery(language_model_wanting_to_draw, artist, INSTRUCTIONS_TEMPLATE)


def test_draws_the_strokes_she_chose(
    illustrator_wanting_to_draw: IllustrateDiscovery, repository: InMemoryDrawingRepository
) -> None:
    illustrator_wanting_to_draw.illustrate(SUN_DISCOVERY)

    assert repository.saved == [SUN_DRAWING]


def test_returns_the_pinned_drawing(illustrator_wanting_to_draw: IllustrateDiscovery) -> None:
    assert illustrator_wanting_to_draw.illustrate(SUN_DISCOVERY) == PinnedDrawing(
        drawing=SUN_DRAWING, file_name=SAVED_FILE_NAME, erased=None
    )


def test_asks_in_the_drawing_decision_schema(
    illustrator_wanting_to_draw: IllustrateDiscovery,
    language_model_wanting_to_draw: ScriptedStructuredLanguageModel,
) -> None:
    illustrator_wanting_to_draw.illustrate(SUN_DISCOVERY)

    assert language_model_wanting_to_draw.received_schemas == [DRAWING_DECISION_SCHEMA]


def test_sends_only_the_instructions_and_the_saved_discovery(
    illustrator_wanting_to_draw: IllustrateDiscovery,
    language_model_wanting_to_draw: ScriptedStructuredLanguageModel,
) -> None:
    illustrator_wanting_to_draw.illustrate(SUN_DISCOVERY)

    assert language_model_wanting_to_draw.received_messages == [
        [
            ChatMessage(Role.SYSTEM, "Lousa 400x300, até 6 traços de 10 pontos."),
            ChatMessage(
                Role.USER,
                "Título: O Sol\nTema: estrelas\nResumo: O Sol é uma estrela gigante.",
            ),
        ]
    ]


def test_returns_none_when_she_does_not_want_to_draw(artist: ChalkboardArtist) -> None:
    illustrator = illustrator_answering(DOES_NOT_WANT_TO_DRAW, artist)

    assert illustrator.illustrate(SUN_DISCOVERY) is None


def test_draws_nothing_when_she_does_not_want_to(
    artist: ChalkboardArtist, repository: InMemoryDrawingRepository
) -> None:
    illustrator_answering(DOES_NOT_WANT_TO_DRAW, artist).illustrate(SUN_DISCOVERY)

    assert repository.saved == []


def test_draws_nothing_when_a_stroke_is_outside_the_board(
    artist: ChalkboardArtist, repository: InMemoryDrawingRepository
) -> None:
    result = illustrator_answering(STROKE_OUTSIDE_THE_BOARD, artist).illustrate(SUN_DISCOVERY)

    assert (result, repository.saved) == (None, [])


def test_draws_nothing_when_a_stroke_has_no_points(
    artist: ChalkboardArtist, repository: InMemoryDrawingRepository
) -> None:
    result = illustrator_answering(STROKE_WITHOUT_POINTS, artist).illustrate(SUN_DISCOVERY)

    assert (result, repository.saved) == (None, [])


def test_returns_none_when_the_model_is_unreachable(artist: ChalkboardArtist) -> None:
    illustrator = IllustrateDiscovery(
        UnreachableStructuredLanguageModel(), artist, INSTRUCTIONS_TEMPLATE
    )

    assert illustrator.illustrate(SUN_DISCOVERY) is None


def test_returns_none_when_the_image_cannot_be_saved() -> None:
    artist = ChalkboardArtist(FullDiskDrawingRepository(), Chalkboard(capacity=3))

    assert illustrator_answering(WANTS_TO_DRAW_THE_SUN, artist).illustrate(SUN_DISCOVERY) is None


def test_logs_why_the_drawing_failed(
    artist: ChalkboardArtist, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.WARNING, logger=ILLUSTRATE_LOGGER)
    illustrator = IllustrateDiscovery(
        UnreachableStructuredLanguageModel(), artist, INSTRUCTIONS_TEMPLATE
    )

    illustrator.illustrate(SUN_DISCOVERY)

    assert caplog.messages == ["Could not draw 'O Sol': connection refused"]


def test_logs_when_she_chooses_not_to_draw(
    artist: ChalkboardArtist, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger=ILLUSTRATE_LOGGER)

    illustrator_answering(DOES_NOT_WANT_TO_DRAW, artist).illustrate(SUN_DISCOVERY)

    assert caplog.messages == ["Chose not to draw: O Sol"]
