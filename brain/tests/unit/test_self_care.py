import pytest

from src.application.self_care import SelfCare
from src.domain.body import Place
from src.domain.feelings.appraisal import EmotionalEvent, EventKind
from src.domain.feelings.emotion import Emotion
from src.domain.feelings.emotional_life import EmotionalLife
from src.domain.feelings.needs import Need
from tests.fakes.emotional_lives import AlwaysRandom, a_life

REST_SECONDS = 600.0


class RecordingBody:
    def __init__(self) -> None:
        self.visited_places: list[Place] = []

    def go_to(self, place: Place) -> None:
        self.visited_places.append(place)


class FixedHeart:
    def __init__(self, life: EmotionalLife) -> None:
        self._life = life
        self.felt: list[EmotionalEvent] = []

    def check_in(self, pending_wishes: int | None = None) -> EmotionalLife:
        return self._life

    def feel(self, event: EmotionalEvent) -> EmotionalLife:
        self.felt.append(event)
        return self._life


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def body() -> RecordingBody:
    return RecordingBody()


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def worn_out_heart() -> FixedHeart:
    return FixedHeart(a_life({Emotion.JOY: 0.4}, needs={Need.COMFORT: 0.2}))


@pytest.fixture
def self_care(worn_out_heart: FixedHeart, body: RecordingBody, clock: FakeClock) -> SelfCare:
    # 0.99 never picks a surprise place, so the place follows from her feelings.
    return SelfCare(
        worn_out_heart, body, rng=AlwaysRandom(0.99), rest_seconds=REST_SECONDS, clock=clock
    )


def test_worn_out_she_walks_to_a_comfort_place(self_care: SelfCare, body: RecordingBody) -> None:
    self_care.take_care()

    assert body.visited_places == [Place.FOOD_BOWL]


def test_taking_care_of_herself_is_felt(self_care: SelfCare, worn_out_heart: FixedHeart) -> None:
    self_care.take_care()

    assert worn_out_heart.felt == [EmotionalEvent(EventKind.VISITED_COMFORT_PLACE)]


def test_right_after_taking_care_she_rests_from_it(
    self_care: SelfCare, body: RecordingBody, clock: FakeClock
) -> None:
    self_care.take_care()
    clock.now += REST_SECONDS - 1

    self_care.take_care()

    assert len(body.visited_places) == 1


def test_after_resting_she_can_take_care_again(
    self_care: SelfCare, body: RecordingBody, clock: FakeClock
) -> None:
    self_care.take_care()
    clock.now += REST_SECONDS

    self_care.take_care()

    assert len(body.visited_places) == 2


def test_feeling_fine_she_stays_where_she_is(body: RecordingBody) -> None:
    content = FixedHeart(a_life({Emotion.JOY: 0.5, Emotion.CURIOSITY: 0.5}))

    SelfCare(content, body).take_care()

    assert body.visited_places == []
