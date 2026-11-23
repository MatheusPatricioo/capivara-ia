import pytest

from src.domain.text_embedding import cosine_similarity


def test_same_direction_is_fully_similar() -> None:
    assert cosine_similarity((1.0, 2.0), (2.0, 4.0)) == pytest.approx(1.0)


def test_perpendicular_vectors_are_unrelated() -> None:
    assert cosine_similarity((1.0, 0.0), (0.0, 3.0)) == pytest.approx(0.0)


def test_opposite_directions_are_fully_dissimilar() -> None:
    assert cosine_similarity((1.0, 1.0), (-1.0, -1.0)) == pytest.approx(-1.0)


def test_ignores_the_length_of_the_vectors() -> None:
    assert cosine_similarity((3.0, 4.0), (30.0, 40.0)) == pytest.approx(1.0)


def test_a_zero_vector_is_unrelated_to_anything() -> None:
    assert cosine_similarity((0.0, 0.0), (1.0, 2.0)) == 0.0


def test_rejects_vectors_of_different_sizes() -> None:
    with pytest.raises(ValueError, match="sizes 2 and 3"):
        cosine_similarity((1.0, 2.0), (1.0, 2.0, 3.0))
