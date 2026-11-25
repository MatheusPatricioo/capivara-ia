-- RAG v2: each discovery is also stored in pieces (chunks), searched two ways at once:
-- by meaning (embedding, pgvector) and by words (full-text search, tsvector).
-- Runs on the first start of an empty volume; the brain also applies it on start-up,
-- so an existing database gets it too (every statement is IF NOT EXISTS / OR REPLACE).

-- unaccent: "vitória-régia" and "vitoria regia" become the same words.
CREATE EXTENSION IF NOT EXISTS unaccent;

-- A generated column only accepts IMMUTABLE functions, and unaccent() is only STABLE
-- (its dictionary could change). This wrapper pins the dictionary, which makes it safe.
CREATE OR REPLACE FUNCTION immutable_unaccent(text)
    RETURNS text
    LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT
AS $$ SELECT public.unaccent('public.unaccent'::regdictionary, $1) $$;

CREATE TABLE IF NOT EXISTS discovery_chunks (
    id            BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    discovery_id  BIGINT      NOT NULL REFERENCES discoveries (id) ON DELETE CASCADE,
    position      INTEGER     NOT NULL,
    content       TEXT        NOT NULL,
    embedding     VECTOR(768) NOT NULL,
    -- Words reduced to their stems in Portuguese ("nadam", "nadando" -> "nad"), without
    -- accents; computed by PostgreSQL itself whenever content changes.
    search_vector TSVECTOR    GENERATED ALWAYS AS (
        to_tsvector('portuguese', immutable_unaccent(content))
    ) STORED,
    UNIQUE (discovery_id, position)
);

CREATE INDEX IF NOT EXISTS discovery_chunks_embedding_hnsw_index
    ON discovery_chunks USING hnsw (embedding vector_cosine_ops);

-- GIN: the inverted index of full-text search (word -> rows that contain it).
CREATE INDEX IF NOT EXISTS discovery_chunks_search_vector_gin_index
    ON discovery_chunks USING gin (search_vector);
