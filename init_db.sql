-- Run this SQL in your Supabase SQL Editor to create the necessary table

CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY,
    source TEXT,
    page INTEGER,
    chunk_index INTEGER,
    content TEXT
);

-- Enable full text search index for fast keyword search (BM25 equivalent)
CREATE INDEX IF NOT EXISTS documents_content_idx ON documents USING GIN (to_tsvector('english', content));
