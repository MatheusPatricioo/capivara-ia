import pytest

from src.domain.attention import Attention, PointOfAttention

CAPACITY = 3
REST_SECONDS = 600.0
NOW = 1000.0

LILIES = PointOfAttention("water_lilies", "vitórias-régias no laguinho")
MUSHROOMS = PointOfAttention("mushrooms", "cogumelos vermelhos")
OAK = PointOfAttention("big_oak", "um carvalho enorme")
STUMP = PointOfAttention("old_stump", "um toco velho")


def notice(attention: Attention, point: PointOfAttention, now: float = NOW) -> bool:
    return attention.notice(point.thing_id, point.description, now)


@pytest.fixture
def attention() -> Attention:
    return Attention(capacity=CAPACITY, rest_seconds=REST_SECONDS)


@pytest.fixture
def full_attention(attention: Attention) -> Attention:
    for point in (LILIES, MUSHROOMS, OAK):
        notice(attention, point)
    return attention


def test_starts_with_nothing_pending(attention: Attention) -> None:
    assert attention.pending == ()


def test_a_new_thing_becomes_a_point_of_attention(attention: Attention) -> None:
    assert notice(attention, LILIES) is True
    assert attention.pending == (LILIES,)


def test_lists_the_most_recent_things_first(full_attention: Attention) -> None:
    assert full_attention.pending == (OAK, MUSHROOMS, LILIES)


def test_a_thing_already_waiting_is_not_added_twice(attention: Attention) -> None:
    notice(attention, LILIES)

    assert notice(attention, LILIES) is False
    assert attention.pending == (LILIES,)


def test_forgets_the_oldest_thing_when_full(full_attention: Attention) -> None:
    notice(full_attention, STUMP)

    assert full_attention.pending == (STUMP, OAK, MUSHROOMS)


def test_letting_go_removes_the_thing_from_the_list(full_attention: Attention) -> None:
    full_attention.let_go(MUSHROOMS.thing_id, NOW)

    assert full_attention.pending == (OAK, LILIES)


def test_a_thing_let_go_cannot_catch_her_eye_while_resting(attention: Attention) -> None:
    notice(attention, LILIES)
    attention.let_go(LILIES.thing_id, NOW)

    assert notice(attention, LILIES, now=NOW + REST_SECONDS - 1) is False
    assert attention.pending == ()


def test_a_thing_catches_her_eye_again_after_resting(attention: Attention) -> None:
    notice(attention, LILIES)
    attention.let_go(LILIES.thing_id, NOW)

    assert notice(attention, LILIES, now=NOW + REST_SECONDS) is True


def test_letting_go_of_an_unknown_thing_changes_nothing(full_attention: Attention) -> None:
    full_attention.let_go("unknown_thing", NOW)

    assert full_attention.pending == (OAK, MUSHROOMS, LILIES)


def test_rejects_a_capacity_that_is_not_positive() -> None:
    with pytest.raises(ValueError, match="capacity"):
        Attention(capacity=0, rest_seconds=REST_SECONDS)


def test_rejects_a_negative_rest_time() -> None:
    with pytest.raises(ValueError, match="rest_seconds"):
        Attention(capacity=CAPACITY, rest_seconds=-1)
