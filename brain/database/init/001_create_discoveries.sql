-- Long-term memory: one row per saved discovery, with its text, metadata and embedding.
-- Runs once, on the first start of an empty database volume.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS discoveries (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    -- The Markdown file in the discoveries folder; unique, so indexing twice is harmless.
    file_name     TEXT        NOT NULL UNIQUE,
    title         TEXT        NOT NULL,
    topic         TEXT        NOT NULL,
    summary       TEXT        NOT NULL,
    sources       TEXT[]      NOT NULL,
    discovered_on DATE        NOT NULL,
    -- nomic-embed-text returns 768 numbers per text.
    embedding     VECTOR(768) NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Approximate nearest neighbours by cosine distance (the <=> operator).
CREATE INDEX IF NOT EXISTS discoveries_embedding_hnsw_index
    ON discoveries USING hnsw (embedding vector_cosine_ops);
