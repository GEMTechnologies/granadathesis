-- Database Performance Optimizations

-- 1. Indexes for Fast Lookups
CREATE INDEX IF NOT EXISTS idx_objectives_thesis_id ON objectives(thesis_id);
CREATE INDEX IF NOT EXISTS idx_objectives_created_at ON objectives(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_voting_sessions_thesis_id ON voting_sessions(thesis_id);
CREATE INDEX IF NOT EXISTS idx_voting_sessions_created_at ON voting_sessions(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_chapters_thesis_id ON chapters(thesis_id);
CREATE INDEX IF NOT EXISTS idx_chapters_number ON chapters(chapter_number);

-- 2. Composite Indexes for Common Queries
CREATE INDEX IF NOT EXISTS idx_objectives_thesis_type ON objectives(thesis_id, type);
CREATE INDEX IF NOT EXISTS idx_votes_session_number ON votes(session_id, sample_number);

-- 3. Partial Indexes for Filtered Queries
CREATE INDEX IF NOT EXISTS idx_active_objectives 
ON objectives(thesis_id) 
WHERE deleted_at IS NULL;

-- 4. GIN Indexes for Full-Text Search (if needed)
CREATE INDEX IF NOT EXISTS idx_objectives_text_search 
ON objectives USING GIN(to_tsvector('english', text));

-- 5. Statistics Update for Query Planner
ANALYZE objectives;
ANALYZE voting_sessions;
ANALYZE votes;
ANALYZE chapters;

-- 6. Vacuum for Performance
VACUUM ANALYZE;
