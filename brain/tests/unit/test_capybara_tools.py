from pathlib import Path

import pytest

from src.capybara_tools import build_capybara_tools
from src.domain.chalkboard import Chalkboard
from src.domain.language_model import ChatMessage, StructuredReply
from src.infrastructure.settings import Settings


class NeverAskedStructuredLanguageModel:
    def complete_json(
        self, messages: list[ChatMessage], schema: dict[str, object]
    ) -> StructuredReply:
        raise AssertionError("building the tools must not call the model")


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(_env_file=None, discoveries_dir=tmp_path)


def test_offers_only_search_and_save_because_drawing_is_automatic(settings: Settings) -> None:
    tools = build_capybara_tools(settings, Chalkboard(3), NeverAskedStructuredLanguageModel())

    assert [tool.definition.name for tool in tools] == ["web_search", "save_discovery"]
