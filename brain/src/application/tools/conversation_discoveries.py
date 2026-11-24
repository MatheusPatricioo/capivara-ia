from src.domain.discovery import Discovery


class ConversationDiscoveries:
    """Remembers the discoveries saved in the current conversation (one cycle of the live mode).

    Shared between save_discovery, which fills it, and suggest_improvement, which takes the
    latest one as the inspiration: the model never names the inspiration itself, so it
    cannot cite a discovery that does not exist.
    """

    def __init__(self) -> None:
        self._saved: list[Discovery] = []

    def remember(self, discovery: Discovery) -> None:
        self._saved.append(discovery)

    @property
    def latest(self) -> Discovery | None:
        return self._saved[-1] if self._saved else None
