from enum import StrEnum
from typing import Any, Final

import psycopg
from psycopg import Connection
from psycopg.conninfo import make_conninfo
from psycopg.rows import TupleRow
from psycopg_pool import ConnectionPool

from src.domain.discovery import Discovery
from src.domain.discovery_chunks import discovery_chunks
from src.domain.discovery_memory import DiscoveryMemoryError, RememberedDiscovery
from src.domain.text_embedding import Embedding, EmbeddingError, TextEmbedder

MemoryPool = ConnectionPool[Connection[TupleRow]]

# Must match VECTOR(768) in brain/database/init/ (nomic-embed-text returns 768 numbers).
EMBEDDING_DIMENSIONS: Final = 768

# How many discoveries each search (meaning, words) proposes before they are fused.
HYBRID_CANDIDATES: Final = 20
# The k of Reciprocal Rank Fusion: score = 1/(k + rank). 60 is the value from the original
# paper (Cormack et al., 2009); it keeps one list's first place from dominating the other.
RRF_K: Final = 60


class SearchMode(StrEnum):
    VECTOR = "vector"
    """Only the whole-discovery embedding (the first version of the memory)."""
    HYBRID = "hybrid"
    """Chunks searched by meaning and by words, fused with Reciprocal Rank Fusion."""


# Remembering the same file again replaces the row instead of failing on UNIQUE (file_name).
UPSERT_DISCOVERY: Final = """
    INSERT INTO discoveries (file_name, title, topic, summary, sources, discovered_on, embedding)
    VALUES (
        %(file_name)s, %(title)s, %(topic)s, %(summary)s,
        %(sources)s, %(discovered_on)s, %(embedding)s::vector
    )
    ON CONFLICT (file_name) DO UPDATE SET
        title         = EXCLUDED.title,
        topic         = EXCLUDED.topic,
        summary       = EXCLUDED.summary,
        sources       = EXCLUDED.sources,
        discovered_on = EXCLUDED.discovered_on,
        embedding     = EXCLUDED.embedding
    RETURNING id
"""

DELETE_CHUNKS: Final = "DELETE FROM discovery_chunks WHERE discovery_id = %(discovery_id)s"

INSERT_CHUNK: Final = """
    INSERT INTO discovery_chunks (discovery_id, position, content, embedding)
    VALUES (%(discovery_id)s, %(position)s, %(content)s, %(embedding)s::vector)
"""

# <=> is the cosine distance (0 same direction, 2 opposite), so similarity = 1 - distance.
# Ordering by the distance itself (not by the similarity) lets PostgreSQL use the HNSW index.
RECALL_CLOSEST: Final = """
    SELECT title, topic, summary, sources, discovered_on,
           1 - (embedding <=> %(query)s::vector) AS similarity
    FROM discoveries
    ORDER BY embedding <=> %(query)s::vector
    LIMIT %(limit)s
"""

# Hybrid search in one query:
# 1. by_meaning: the closest chunk of each discovery, ranked by cosine distance.
# 2. by_words: full-text search. plainto_tsquery joins the words with AND (&), which would
#    demand every word; turning & into | (OR) lets any shared word count, and ts_rank_cd
#    ranks the chunks that share more (and closer) words higher.
# 3. fused: Reciprocal Rank Fusion, 1/(k + rank) summed over both lists. Ranks, not scores,
#    are fused, because a cosine similarity and a ts_rank live on different scales.
# The similarity returned is the cosine similarity of the discovery's closest chunk, so the
# callers can still log it and filter on it.
RECALL_HYBRID: Final = """
    WITH by_meaning AS (
        SELECT discovery_id,
               ROW_NUMBER() OVER (ORDER BY MIN(embedding <=> %(query)s::vector)) AS rank
        FROM discovery_chunks
        GROUP BY discovery_id
        ORDER BY rank
        LIMIT %(candidates)s
    ),
    text_query AS (
        SELECT to_tsquery(
            'portuguese',
            replace(
                plainto_tsquery('portuguese', immutable_unaccent(%(text)s))::text, ' & ', ' | '
            )
        ) AS query
    ),
    by_words AS (
        SELECT discovery_id,
               ROW_NUMBER() OVER (ORDER BY MAX(ts_rank_cd(search_vector, query)) DESC) AS rank
        FROM discovery_chunks, text_query
        WHERE search_vector @@ query
        GROUP BY discovery_id
        ORDER BY rank
        LIMIT %(candidates)s
    ),
    fused AS (
        SELECT COALESCE(by_meaning.discovery_id, by_words.discovery_id) AS discovery_id,
               COALESCE(1.0 / (%(rrf_k)s + by_meaning.rank), 0)
                 + COALESCE(1.0 / (%(rrf_k)s + by_words.rank), 0) AS score
        FROM by_meaning
        FULL OUTER JOIN by_words ON by_meaning.discovery_id = by_words.discovery_id
    )
    SELECT discoveries.title, discoveries.topic, discoveries.summary, discoveries.sources,
           discoveries.discovered_on,
           1 - (
               SELECT MIN(chunk.embedding <=> %(query)s::vector)
               FROM discovery_chunks AS chunk
               WHERE chunk.discovery_id = discoveries.id
           ) AS similarity
    FROM fused
    JOIN discoveries ON discoveries.id = fused.discovery_id
    ORDER BY fused.score DESC, similarity DESC
    LIMIT %(limit)s
"""


class PostgresDiscoveryMemory:
    """DiscoveryMemory stored in PostgreSQL: pgvector for meaning, full-text for words.

    Every discovery is stored whole (one embedding) and in chunks (one embedding and one
    tsvector each). search_mode chooses how recall searches them (see SearchMode).

    Embeddings are computed before taking a connection from the pool, so no connection
    sits idle while Ollama thinks. query_embedder embeds the searches (it may add a task
    prefix such as "search_query: "); by default it is the same as the document embedder.
    Any failure (embedder, database) becomes a DiscoveryMemoryError.
    """

    def __init__(
        self,
        pool: MemoryPool,
        embedder: TextEmbedder,
        query_embedder: TextEmbedder | None = None,
        search_mode: SearchMode = SearchMode.HYBRID,
    ) -> None:
        self._pool = pool
        self._embedder = embedder
        self._query_embedder = query_embedder or embedder
        self._search_mode = search_mode

    def remember(self, file_name: str, discovery: Discovery) -> None:
        chunks = discovery_chunks(discovery)
        # The first chunk is memory_text(discovery): its embedding is the whole-discovery one.
        chunk_embeddings = self._embed(self._embedder, chunks)
        parameters = {
            "file_name": file_name,
            "title": discovery.title,
            "topic": discovery.topic,
            "summary": discovery.summary,
            "sources": list(discovery.sources),
            "discovered_on": discovery.discovered_on,
            "embedding": chunk_embeddings[0],
        }
        try:
            # One connection block is one transaction: the discovery and its chunks are
            # replaced together, or not at all.
            with self._pool.connection() as connection:
                row = connection.execute(UPSERT_DISCOVERY, parameters).fetchone()
                if row is None:
                    raise DiscoveryMemoryError(f"Could not remember {file_name}: no id returned")
                self._replace_chunks(connection, row[0], chunks, chunk_embeddings)
        except psycopg.Error as error:
            raise DiscoveryMemoryError(f"Could not remember {file_name}: {error}") from error

    def recall(self, text: str, limit: int) -> list[RememberedDiscovery]:
        [query] = self._embed(self._query_embedder, [text])
        if self._search_mode is SearchMode.VECTOR:
            sql, parameters = RECALL_CLOSEST, {"query": query, "limit": limit}
        else:
            sql = RECALL_HYBRID
            parameters = {
                "query": query,
                "text": text,
                "limit": limit,
                "candidates": max(limit, HYBRID_CANDIDATES),
                "rrf_k": RRF_K,
            }
        try:
            with self._pool.connection() as connection:
                rows = connection.execute(sql, parameters).fetchall()
        except psycopg.Error as error:
            raise DiscoveryMemoryError(f"Could not recall discoveries: {error}") from error
        return [self._to_remembered(row) for row in rows]

    @staticmethod
    def _replace_chunks(
        connection: Connection[TupleRow],
        discovery_id: int,
        chunks: list[str],
        embeddings: list[str],
    ) -> None:
        connection.execute(DELETE_CHUNKS, {"discovery_id": discovery_id})
        chunk_rows = [
            {
                "discovery_id": discovery_id,
                "position": position,
                "content": content,
                "embedding": embedding,
            }
            for position, (content, embedding) in enumerate(zip(chunks, embeddings, strict=True))
        ]
        # executemany sends every chunk in one pipeline, instead of one round trip per chunk.
        with connection.cursor() as cursor:
            cursor.executemany(INSERT_CHUNK, chunk_rows)

    @staticmethod
    def _embed(embedder: TextEmbedder, texts: list[str]) -> list[str]:
        try:
            embeddings = embedder.embed(texts)
        except EmbeddingError as error:
            raise DiscoveryMemoryError(f"Could not embed the memory text: {error}") from error
        return [to_vector_literal(embedding) for embedding in embeddings]

    @staticmethod
    def _to_remembered(row: tuple[Any, ...]) -> RememberedDiscovery:
        title, topic, summary, sources, discovered_on, similarity = row
        discovery = Discovery(
            title=title,
            topic=topic,
            summary=summary,
            sources=tuple(sources),
            discovered_on=discovered_on,
        )
        return RememberedDiscovery(discovery, float(similarity))


def to_vector_literal(embedding: Embedding) -> str:
    """The embedding in pgvector's text format, "[0.1,0.2,...]", which SQL casts with ::vector.

    The size is checked here so a wrong embedding model fails with a clear message
    instead of a database error.
    """
    if len(embedding) != EMBEDDING_DIMENSIONS:
        raise DiscoveryMemoryError(
            f"The embedding has {len(embedding)} numbers, but the memory stores "
            f"{EMBEDDING_DIMENSIONS}: OLLAMA_EMBEDDING_MODEL must be a "
            f"{EMBEDDING_DIMENSIONS}-dimension model like nomic-embed-text"
        )
    return "[" + ",".join(str(value) for value in embedding) + "]"


def memory_conninfo(host: str, port: int, database: str, user: str, password: str) -> str:
    """The libpq connection string, with values quoted when needed (spaces, quotes...)."""
    return make_conninfo(host=host, port=port, dbname=database, user=user, password=password)


def create_memory_pool(conninfo: str, timeout_seconds: float) -> MemoryPool:
    """A small pool of connections, opened with `with create_memory_pool(...) as pool:`.

    - min_size=1, max_size=2: one memory call at a time is the norm; the second is a spare.
    - check: tests each connection before lending it, so a database restart does not
      leave a dead connection behind.
    - timeout: how long a call waits for a connection before giving up (database offline).
    """
    return ConnectionPool(
        conninfo,
        min_size=1,
        max_size=2,
        timeout=timeout_seconds,
        check=ConnectionPool.check_connection,
        name="discovery-memory",
        open=False,
    )
