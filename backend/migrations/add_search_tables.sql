-- Add Search System Tables
-- These tables support caching, search history, saved papers, and collections

-- Search history table
CREATE TABLE IF NOT EXISTS search_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query TEXT NOT NULL,
    filters JSONB,
    api_sources TEXT[],
    results_count INTEGER,
    cache_hit BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_search_history_query ON search_history(query);
CREATE INDEX IF NOT EXISTS idx_search_history_created_at ON search_history(created_at DESC);

-- Saved papers table
CREATE TABLE IF NOT EXISTS saved_papers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doi TEXT UNIQUE,
    title TEXT NOT NULL,
    authors JSONB,
    year INTEGER,
    abstract TEXT,
    url TEXT,
    pdf_path TEXT,
    source TEXT,
    citations INTEGER DEFAULT 0,
    venue TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_saved_papers_doi ON saved_papers(doi);
CREATE INDEX IF NOT EXISTS idx_saved_papers_title ON saved_papers USING gin(to_tsvector('english', title));
CREATE INDEX IF NOT EXISTS idx_saved_papers_created_at ON saved_papers(created_at DESC);

-- Paper collections table
CREATE TABLE IF NOT EXISTS paper_collections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT,
    color TEXT DEFAULT '#3B82F6',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Collection papers (many-to-many)
CREATE TABLE IF NOT EXISTS collection_papers (
    collection_id UUID REFERENCES paper_collections(id) ON DELETE CASCADE,
    paper_id UUID REFERENCES saved_papers(id) ON DELETE CASCADE,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    PRIMARY KEY (collection_id, paper_id)
);

CREATE INDEX IF NOT EXISTS idx_collection_papers_collection ON collection_papers(collection_id);
CREATE INDEX IF NOT EXISTS idx_collection_papers_paper ON collection_papers(paper_id);

-- Citation network table
CREATE TABLE IF NOT EXISTS citations (
    citing_paper_doi TEXT NOT NULL,
    cited_paper_doi TEXT NOT NULL,
    context TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (citing_paper_doi, cited_paper_doi)
);

CREATE INDEX IF NOT EXISTS idx_citations_citing ON citations(citing_paper_doi);
CREATE INDEX IF NOT EXISTS idx_citations_cited ON citations(cited_paper_doi);

-- Paper downloads tracking
CREATE TABLE IF NOT EXISTS paper_downloads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paper_id UUID REFERENCES saved_papers(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    file_size_bytes BIGINT,
    download_source TEXT,
    downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_paper_downloads_paper ON paper_downloads(paper_id);

-- Saved searches table
CREATE TABLE IF NOT EXISTS saved_searches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    query TEXT NOT NULL,
    filters JSONB,
    api_sources TEXT[],
    alert_enabled BOOLEAN DEFAULT FALSE,
    alert_frequency TEXT DEFAULT 'weekly',
    last_run_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_saved_searches_name ON saved_searches(name);
CREATE INDEX IF NOT EXISTS idx_saved_searches_alert ON saved_searches(alert_enabled) WHERE alert_enabled = TRUE;

-- Author tracking table
CREATE TABLE IF NOT EXISTS tracked_authors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    orcid TEXT,
    semantic_scholar_id TEXT,
    openalex_id TEXT,
    h_index INTEGER,
    total_citations INTEGER,
    paper_count INTEGER,
    last_updated_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tracked_authors_name ON tracked_authors(name);
CREATE INDEX IF NOT EXISTS idx_tracked_authors_orcid ON tracked_authors(orcid);

-- Comments/notes on papers
CREATE TABLE IF NOT EXISTS paper_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paper_id UUID REFERENCES saved_papers(id) ON DELETE CASCADE,
    note_text TEXT NOT NULL,
    tags TEXT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_paper_notes_paper ON paper_notes(paper_id);
CREATE INDEX IF NOT EXISTS idx_paper_notes_tags ON paper_notes USING gin(tags);

-- Full-text search index (for extracted PDF text)
CREATE TABLE IF NOT EXISTS paper_fulltext (
    paper_id UUID PRIMARY KEY REFERENCES saved_papers(id) ON DELETE CASCADE,
    fulltext TEXT NOT NULL,
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    extraction_method TEXT
);

CREATE INDEX IF NOT EXISTS idx_paper_fulltext_search ON paper_fulltext USING gin(to_tsvector('english', fulltext));

-- API usage statistics
CREATE TABLE IF NOT EXISTS api_usage_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    api_name TEXT NOT NULL,
    endpoint TEXT,
    query TEXT,
    response_time_ms INTEGER,
    status_code INTEGER,
    cache_hit BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_api_usage_api_name ON api_usage_stats(api_name);
CREATE INDEX IF NOT EXISTS idx_api_usage_created_at ON api_usage_stats(created_at DESC);

-- Update triggers for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_saved_papers_updated_at BEFORE UPDATE ON saved_papers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_paper_collections_updated_at BEFORE UPDATE ON paper_collections
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_paper_notes_updated_at BEFORE UPDATE ON paper_notes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Comments
COMMENT ON TABLE search_history IS 'Tracks all search queries and their results';
COMMENT ON TABLE saved_papers IS 'User-saved academic papers with metadata';
COMMENT ON TABLE paper_collections IS 'Organized collections of papers (like folders)';
COMMENT ON TABLE collection_papers IS 'Many-to-many relationship between collections and papers';
COMMENT ON TABLE citations IS 'Citation network - which papers cite which';
COMMENT ON TABLE paper_downloads IS 'Tracks downloaded PDF files';
COMMENT ON TABLE saved_searches IS 'Saved search queries for re-running and alerts';
COMMENT ON TABLE tracked_authors IS 'Authors being tracked for new publications';
COMMENT ON TABLE paper_notes IS 'User notes and tags on papers';
COMMENT ON TABLE paper_fulltext IS 'Extracted full-text from PDFs for searching';
COMMENT ON TABLE api_usage_stats IS 'API usage statistics and performance monitoring';
