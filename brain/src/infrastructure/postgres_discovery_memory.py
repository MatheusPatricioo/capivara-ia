from typing import Any, Final

import psycopg
from psycopg import Connection
from psycopg.conninfo import make_conninfo
from psycopg.rows import TupleRow
from psycopg_pool import ConnectionPool

from src.domain.discovery import Discovery
from src.domain.discovery_memory import DiscoveryMemoryError, RememberedDiscovery, memory_text
from src.domain.text_embedding import Embedding, EmbeddingError, TextEmbedder

MemoryPool = ConnectionPool[Connection[TupleRow]]

# Must match VECTOR(768) in brain/database/init/001_create_discoveries.sql
# (nomic-embed-text returns 768 numbers per text).
EMBEDDING_DIMENSIONS: Final = 768

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


class PostgresDiscoveryMemory:
    """DiscoveryMemory stored in PostgreSQL, searched by meaning with pgvector.

    The embedding is computed before taking a connection from the pool, so no connection
    sits idle while Ollama thinks. Any failure (embedder, database) becomes a
    DiscoveryMemoryError: the callers only know the domain error.
    """

    def __init__(self, pool: MemoryPool, embedder: TextEmbedder) -> None:
        self._pool = pool
        self._embedder = embedder

    def remember(self, file_name: str, discovery: Discovery) -> None:
        embedding = self._embed(memory_text(discovery))
        parameters = {
            "file_name": file_name,
            "title": discovery.title,
            "topic": discovery.topic,
            "summary": discovery.summary,
            "sources": list(discovery.sources),
            "discovered_on": discovery.discovered_on,
            "embedding": embedding,
        }
        try:
            with self._pool.connection() as connection:
                connection.execute(UPSERT_DISCOVERY, parameters)
        except psycopg.Error as error:
            raise DiscoveryMemoryError(f"Could not remember {file_name}: {error}") from error

    def recall(self, text: str, limit: int) -> list[RememberedDiscovery]:
        parameters = {"query": self._embed(text), "limit": limit}
        try:
            with self._pool.connection() as connection:
                rows = connection.execute(RECALL_CLOSEST, parameters).fetchall()
        except psycopg.Error as error:
            raise DiscoveryMemoryError(f"Could not recall discoveries: {error}") from error
        return [self._to_remembered(row) for row in rows]

    def _embed(self, text: str) -> str:
        try:
            [embedding] = self._embedder.embed([text])
        except EmbeddingError as error:
            raise DiscoveryMemoryError(f"Could not embed the memory text: {error}") from error
        return to_vector_literal(embedding)

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
