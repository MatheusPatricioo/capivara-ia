"""Builds her diary: one Markdown page per day, shown on the writing desk of the world."""

from src.application.diary_keeper import DiaryKeeper
from src.application.shown_diary import ShownDiary
from src.infrastructure.markdown_diary import MarkdownDiary
from src.infrastructure.settings import Settings
from src.infrastructure.websocket_diary_display import WebSocketDiaryDisplay
from src.infrastructure.world_server import WorldServer


def build_diary_keeper(settings: Settings, world: WorldServer) -> DiaryKeeper:
    """Her diary, shown in the world right away and after every new entry."""
    diary = ShownDiary(
        MarkdownDiary(settings.discoveries_dir),
        WebSocketDiaryDisplay(world),
        shown_days=settings.diary_shown_days,
    )
    diary.show()
    return DiaryKeeper(diary)
