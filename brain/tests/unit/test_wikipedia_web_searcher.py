import httpx
import pytest

from src.domain.web_search import SearchResult, WebSearchError
from src.infrastructure.wikipedia_web_searcher import WikipediaWebSearcher

QUERY = "insetos noturnos bioluminescentes"
MAX_RESULTS = 2
CONTACT = "https://example.com/capivara"
# Wikipedia does not list the pages in order of relevance: "index" carries the order.
TWO_PAGES_ANSWER = {
    "batchcomplete": True,
    "query": {
        "pages": [
            {
                "title": "Bioluminescência em cupinzeiros",
                "index": 2,
                "fullurl": "https://pt.wikipedia.org/wiki/Bioluminesc%C3%AAncia_em_cupinzeiros",
                "extract": "Cupinzeiros que brilham.",
            },
            {
                "title": "Bioluminescência",
                "index": 1,
                "fullurl": "https://pt.wikipedia.org/wiki/Bioluminesc%C3%AAncia",
                "extract": "Produção de luz por um organismo.",
            },
        ]
    },
}


class RecordingTransport(httpx.BaseTransport):
    """Fake Wikipedia: answers two pages and records the requests."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return httpx.Response(200, json=TWO_PAGES_ANSWER)


@pytest.fixture
def transport() -> RecordingTransport:
    return RecordingTransport()


@pytest.fixture
def wikipedia(transport: RecordingTransport) -> WikipediaWebSearcher:
    return WikipediaWebSearcher(httpx.Client(transport=transport), contact=CONTACT)


def answering(status_code: int, body: object) -> WikipediaWebSearcher:
    transport = httpx.MockTransport(lambda request: httpx.Response(status_code, json=body))
    return WikipediaWebSearcher(httpx.Client(transport=transport), contact=CONTACT)


def test_returns_the_articles_in_order_of_relevance(wikipedia: WikipediaWebSearcher) -> None:
    assert wikipedia.search(QUERY, MAX_RESULTS) == [
        SearchResult(
            "Bioluminescência",
            "https://pt.wikipedia.org/wiki/Bioluminesc%C3%AAncia",
            "Produção de luz por um organismo.",
        ),
        SearchResult(
            "Bioluminescência em cupinzeiros",
            "https://pt.wikipedia.org/wiki/Bioluminesc%C3%AAncia_em_cupinzeiros",
            "Cupinzeiros que brilham.",
        ),
    ]


def test_searches_the_whole_text_for_the_query(
    wikipedia: WikipediaWebSearcher, transport: RecordingTransport
) -> None:
    wikipedia.search(QUERY, MAX_RESULTS)

    params = transport.requests[0].url.params
    assert (params["generator"], params["gsrsearch"], params["gsrlimit"]) == (
        "search",
        QUERY,
        "2",
    )


def test_searches_the_wikipedia_of_the_configured_language(transport: RecordingTransport) -> None:
    wikipedia = WikipediaWebSearcher(httpx.Client(transport=transport), CONTACT, language="es")

    wikipedia.search(QUERY, MAX_RESULTS)

    assert transport.requests[0].url.host == "es.wikipedia.org"


def test_tells_wikipedia_who_is_asking(
    wikipedia: WikipediaWebSearcher, transport: RecordingTransport
) -> None:
    wikipedia.search(QUERY, MAX_RESULTS)

    assert CONTACT in transport.requests[0].headers["User-Agent"]


def test_finds_nothing_when_wikipedia_answers_without_a_query() -> None:
    wikipedia = answering(200, {"batchcomplete": True})

    assert wikipedia.search(QUERY, MAX_RESULTS) == []


def test_a_refused_request_is_a_search_error() -> None:
    wikipedia = answering(403, {"error": "robot policy"})

    with pytest.raises(WebSearchError):
        wikipedia.search(QUERY, MAX_RESULTS)


def test_an_unexpected_answer_is_a_search_error() -> None:
    wikipedia = answering(200, {"query": {"pages": "not a list"}})

    with pytest.raises(WebSearchError):
        wikipedia.search(QUERY, MAX_RESULTS)


def test_an_unreachable_wikipedia_is_a_search_error() -> None:
    def refuse_connection(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no network", request=request)

    wikipedia = WikipediaWebSearcher(
        httpx.Client(transport=httpx.MockTransport(refuse_connection)), CONTACT
    )

    with pytest.raises(WebSearchError):
        wikipedia.search(QUERY, MAX_RESULTS)
