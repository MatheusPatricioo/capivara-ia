from pathlib import PurePath


class SavedDiscoveries:
    """Remembers the discoveries saved in this conversation and which ones already got a drawing.

    A discovery can be found by its title or by the file name it was saved under, because
    models often repeat the file name from the save_discovery result instead of the title.
    """

    def __init__(self) -> None:
        self._titles_by_name: dict[str, str] = {}
        self._drawn_titles: set[str] = set()

    def remember(self, title: str, file_name: str = "") -> None:
        names = [title]
        if file_name:
            names += [file_name, PurePath(file_name).stem]
        for name in names:
            self._titles_by_name[self._normalize(name)] = title.strip()

    def title_for(self, name: str) -> str | None:
        """Returns the real title of a saved discovery, given its title or file name."""
        return self._titles_by_name.get(self._normalize(name))

    def contains(self, name: str) -> bool:
        return self.title_for(name) is not None

    def mark_drawn(self, title: str) -> None:
        self._drawn_titles.add(self._normalize(title))

    def was_drawn(self, title: str) -> bool:
        return self._normalize(title) in self._drawn_titles

    @staticmethod
    def _normalize(name: str) -> str:
        """Ignores case and surrounding spaces, so 'O Sol ' and 'o sol' are the same discovery."""
        return name.strip().casefold()
