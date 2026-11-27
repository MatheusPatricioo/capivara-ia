"""Full-text search on Wikipedia (MediaWiki API): free, no API key.

Unlike the ddgs Wikipedia engine, which only matches article titles, this searches the
whole text of the articles, so a phrase like "insetos noturnos bioluminescentes" still
finds "Bioluminescência". Each result carries the article intro as its snippet.
"""

import httpx
from pydantic import BaseModel, ValidationError

from src.domain.web_search import SearchResult, WebSearchError

API_URL_TEMPLATE = "https://{language}.wikipedia.org/w/api.php"
CLIENT_NAME = "CapivaraIA/0.1"
INTRO_MAX_CHARACTERS = 500


class _Page(BaseModel):
    title: str
    index: int
    fullurl: str
    extract: str = ""


class _Query(BaseModel):
    pages: list[_Page]


class _SearchResponse(BaseModel):
    # Without a match, Wikipedia answers with no "query" at all.
    query: _Query | None = None


def wikipedia_user_agent(contact: str) -> str:
    """Wikipedia's robot policy asks every client to say who it is and how to reach them."""
    return f"{CLIENT_NAME} ({contact}) httpx"


class WikipediaWebSearcher:
    def __init__(
        self,
        client: httpx.Client,
        contact: str,
        language: str = "pt",
        timeout_seconds: float = 10.0,
    ) -> None:
        self._client = client
        self._user_agent = wikipedia_user_agent(contact)
        self._api_url = API_URL_TEMPLATE.format(language=language)
        self._timeout_seconds = timeout_seconds

    def search(self, query: str, max_results: int) -> list[SearchResult]:
        try:
            response = self._client.get(
                self._api_url,
                params=self._search_params(query, max_results),
                headers={"User-Agent": self._user_agent},
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()
            answer = _SearchResponse.model_validate_json(response.content)
        except httpx.HTTPError as error:
            raise WebSearchError(f"Could not reach Wikipedia: {error}") from error
        except ValidationError as error:
            raise WebSearchError("Unexpected answer from Wikipedia") from error
        if answer.query is None:
            return []
        pages_by_relevance = sorted(answer.query.pages, key=lambda page: page.index)
        return [
            SearchResult(title=page.title, url=page.fullurl, snippet=page.extract)
            for page in pages_by_relevance
        ]

    @staticmethod
    def _search_params(query: str, max_results: int) -> dict[str, str | int]:
        """One request brings the matching articles, their links and their intros."""
        return {
            "action": "query",
            "format": "json",
            "formatversion": 2,
            "generator": "search",
            "gsrsearch": query,
            "gsrlimit": max_results,
            "prop": "extracts|info",
            "exintro": 1,
            "explaintext": 1,
            "exchars": INTRO_MAX_CHARACTERS,
            "exlimit": max_results,
            "inprop": "url",
        }
