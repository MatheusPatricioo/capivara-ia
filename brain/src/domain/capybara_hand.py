import math
import random
from dataclasses import dataclass

from src.domain.doodle import DOODLE_BOX_SIZE, Doodle, DoodlePoint, DoodleStroke
from src.domain.drawing import MAX_POINTS_PER_STROKE

FloatPoint = tuple[float, float]


@dataclass(frozen=True)
class HandStyle:
    """How much her hand changes a reference doodle. Lengths are in doodle box units (0-255)."""

    max_tilt_degrees: float = 7.0
    """The whole drawing comes out a little tilted, up to this angle either way."""
    max_stretch: float = 0.12
    """Width and height each grow or shrink by up to this fraction (0.12 = 12%)."""
    max_stroke_shift: float = 5.0
    """Each stroke lands a bit away from where the reference put it."""
    wobble_amplitude: float = 1.6
    """How far her line drifts from a straight one: her slightly shaky signature."""
    wobble_wavelength: float = 70.0
    """Length of one gentle wave of the wobble; long waves look like a hand, not noise."""
    segment_length: float = 16.0
    """Long straight lines are split into pieces this long, so the wobble can bend them."""


STILL_HAND = HandStyle(
    max_tilt_degrees=0.0,
    max_stretch=0.0,
    max_stroke_shift=0.0,
    wobble_amplitude=0.0,
    segment_length=float(DOODLE_BOX_SIZE * 2),
)
"""A hand that changes nothing: the reference is copied as it is."""


class CapybaraHand:
    """Redraws a reference doodle in her own hand, so no two drawings come out the same.

    The shape is the reference's; the tilt, proportions, stroke positions and the gentle
    wobble of the line are hers, chosen at random for every drawing.
    """

    def __init__(self, style: HandStyle = HandStyle(), rng: random.Random | None = None) -> None:
        self._style = style
        self._rng = rng or random.Random()

    def redraw(self, reference: Doodle) -> Doodle:
        tilt = math.radians(self._spread(self._style.max_tilt_degrees))
        stretch = (
            1 + self._spread(self._style.max_stretch),
            1 + self._spread(self._style.max_stretch),
        )
        strokes = [self._redraw_stroke(stroke, tilt, stretch) for stroke in reference.strokes]
        return Doodle(category=reference.category, strokes=_fit_in_the_doodle_box(strokes))

    def _redraw_stroke(
        self, stroke: DoodleStroke, tilt: float, stretch: FloatPoint
    ) -> list[FloatPoint]:
        shift = (
            self._spread(self._style.max_stroke_shift),
            self._spread(self._style.max_stroke_shift),
        )
        phases = (self._rng.uniform(0, math.tau), self._rng.uniform(0, math.tau))
        redrawn = []
        for point, distance in _densify(stroke, self._style.segment_length):
            x, y = _tilt(_stretch(point, stretch), tilt)
            wave = math.tau * distance / self._style.wobble_wavelength
            redrawn.append(
                (
                    x + shift[0] + self._style.wobble_amplitude * math.sin(wave + phases[0]),
                    y + shift[1] + self._style.wobble_amplitude * math.sin(wave + phases[1]),
                )
            )
        return redrawn

    def _spread(self, limit: float) -> float:
        return self._rng.uniform(-limit, limit)


def _densify(stroke: DoodleStroke, segment_length: float) -> list[tuple[FloatPoint, float]]:
    """The stroke's points plus extra ones along long lines, each with its distance from the start.

    Never more than MAX_POINTS_PER_STROKE: the longest lines give up pieces first.
    """
    segments = list(zip(stroke, stroke[1:], strict=False))
    lengths = [math.dist(start, end) for start, end in segments]
    pieces = [max(1, math.ceil(length / segment_length)) for length in lengths]
    while sum(pieces) + 1 > MAX_POINTS_PER_STROKE:
        splittable = [index for index, count in enumerate(pieces) if count > 1]
        longest = max(splittable, key=lambda index: lengths[index] / pieces[index])
        pieces[longest] -= 1
    points: list[tuple[FloatPoint, float]] = []
    travelled = 0.0
    for (start, end), length, piece_count in zip(segments, lengths, pieces, strict=True):
        for piece in range(piece_count):
            fraction = piece / piece_count
            point = (
                start[0] + (end[0] - start[0]) * fraction,
                start[1] + (end[1] - start[1]) * fraction,
            )
            points.append((point, travelled + length * fraction))
        travelled += length
    points.append(((float(stroke[-1][0]), float(stroke[-1][1])), travelled))
    return points


def _stretch(point: FloatPoint, stretch: FloatPoint) -> FloatPoint:
    return point[0] * stretch[0], point[1] * stretch[1]


def _tilt(point: FloatPoint, angle: float) -> FloatPoint:
    cosine, sine = math.cos(angle), math.sin(angle)
    return point[0] * cosine - point[1] * sine, point[0] * sine + point[1] * cosine


def _fit_in_the_doodle_box(strokes: list[list[FloatPoint]]) -> tuple[DoodleStroke, ...]:
    """Moves the drawing back into the 0-255 box, shrinking it only if it grew too big."""
    xs = [x for stroke in strokes for x, _ in stroke]
    ys = [y for stroke in strokes for _, y in stroke]
    size = max(max(xs) - min(xs), max(ys) - min(ys))
    scale = min(1.0, DOODLE_BOX_SIZE / size) if size > 0 else 1.0
    return tuple(
        tuple(_box_point((x - min(xs)) * scale, (y - min(ys)) * scale) for x, y in stroke)
        for stroke in strokes
    )


def _box_point(x: float, y: float) -> DoodlePoint:
    return (
        min(DOODLE_BOX_SIZE, max(0, round(x))),
        min(DOODLE_BOX_SIZE, max(0, round(y))),
    )
