from enum import StrEnum
from typing import Protocol

from src.domain.drawing import Drawing


class Place(StrEnum):
    """Places in the capybara's world. The values match the interaction point ids in Godot."""

    COMPUTER = "computer"
    CHALKBOARD = "chalkboard"
    MURAL = "mural"
    POND = "pond"
    FOOD_BOWL = "food_bowl"
    DOG_HOUSE = "dog_house"


class Body(Protocol):
    """The capybara's virtual body. The brain decides, the body only shows it."""

    def go_to(self, place: Place) -> None: ...

    def show_chalkboard(self, drawings: tuple[Drawing, ...]) -> None: ...
