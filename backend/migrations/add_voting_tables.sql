-- Migration: Add MAKER Framework Voting Tables
-- Created: 2025-11-25
-- Description: Adds tables to track voting sessions, individual votes, and red flag statistics

-- Table: voting_sessions
-- Tracks each voting session (e.g., for generating one set of objectives)
CREATE TABLE IF NOT EXISTS voting_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thesis_id UUID REFERENCES theses(id) ON DELETE CASCADE,
    task_type VARCHAR(50) NOT NULL, -- 'objective', 'paragraph', 'section', etc.
    task_description TEXT,
    k_threshold INTEGER NOT NULL, -- The 'k' value used for first-to-ahead-by-k
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    total_samples INTEGER DEFAULT 0,
    flagged_samples INTEGER DEFAULT 0,
    convergence_rounds INTEGER DEFAULT 0, -- Number of valid votes before consensus
    estimated_cost DECIMAL(10, 4),
    actual_cost DECIMAL(10, 4),
    winner TEXT, -- The winning candidate
    winner_votes INTEGER,
    metadata JSONB -- Additional session data
);

-- Table: votes
-- Tracks individual votes within a session
CREATE TABLE IF NOT EXISTS votes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES voting_sessions(id) ON DELETE CASCADE,
    sample_number INTEGER NOT NULL, -- Order in which sample was generated
    model_used VARCHAR(100), -- e.g., 'deepseek', 'gpt-4', etc.
    temperature DECIMAL(3, 2), -- Temperature used for this sample
    response_text TEXT, -- Full LLM response
    parsed_result JSONB, -- Parsed/validated result
    was_flagged BOOLEAN DEFAULT FALSE,
    flag_reasons TEXT[], -- Array of flag reasons if flagged
    vote_for TEXT, -- The candidate this vote supports (NULL if flagged)
    created_at TIMESTAMP DEFAULT NOW()
);

-- Table: red_flag_stats
-- Aggregated statistics about red flags for analysis
CREATE TABLE IF NOT EXISTS red_flag_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    flag_type VARCHAR(100) NOT NULL, -- e.g., 'length_exceeded', 'format_invalid', 'methodology_creep'
    task_type VARCHAR(50), -- What type of task this flag appeared in
    count INTEGER DEFAULT 1,
    last_seen TIMESTAMP DEFAULT NOW(),
    examples TEXT[] DEFAULT '{}', -- Store up to 5 example responses
    UNIQUE(flag_type, task_type)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_voting_sessions_thesis_id ON voting_sessions(thesis_id);
CREATE INDEX IF NOT EXISTS idx_voting_sessions_task_type ON voting_sessions(task_type);
CREATE INDEX IF NOT EXISTS idx_voting_sessions_created_at ON voting_sessions(created_at);
CREATE INDEX IF NOT EXISTS idx_votes_session_id ON votes(session_id);
CREATE INDEX IF NOT EXISTS idx_votes_was_flagged ON votes(was_flagged);
CREATE INDEX IF NOT EXISTS idx_red_flag_stats_flag_type ON red_flag_stats(flag_type);

-- Function to update red flag stats
CREATE OR REPLACE FUNCTION update_red_flag_stats()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.was_flagged = TRUE AND NEW.flag_reasons IS NOT NULL THEN
        -- Update stats for each flag reason
        FOREACH flag_reason IN ARRAY NEW.flag_reasons
        LOOP
            INSERT INTO red_flag_stats (flag_type, task_type, count, last_seen, examples)
            SELECT 
                flag_reason,
                vs.task_type,
                1,
                NOW(),
                ARRAY[LEFT(NEW.response_text, 200)]
            FROM voting_sessions vs
            WHERE vs.id = NEW.session_id
            ON CONFLICT (flag_type, task_type) 
            DO UPDATE SET
                count = red_flag_stats.count + 1,
                last_seen = NOW(),
                examples = CASE 
                    WHEN array_length(red_flag_stats.examples, 1) < 5 
                    THEN red_flag_stats.examples || LEFT(NEW.response_text, 200)
                    ELSE red_flag_stats.examples
                END;
        END LOOP;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to automatically update red flag stats
DROP TRIGGER IF EXISTS trigger_update_red_flag_stats ON votes;
CREATE TRIGGER trigger_update_red_flag_stats
    AFTER INSERT ON votes
    FOR EACH ROW
    EXECUTE FUNCTION update_red_flag_stats();

-- Function to get voting session summary
CREATE OR REPLACE FUNCTION get_voting_session_summary(session_uuid UUID)
RETURNS TABLE (
    session_id UUID,
    task_type VARCHAR,
    k_threshold INTEGER,
    total_samples INTEGER,
    flagged_samples INTEGER,
    valid_samples INTEGER,
    convergence_rounds INTEGER,
    winner TEXT,
    winner_votes INTEGER,
    vote_distribution JSONB,
    flag_distribution JSONB,
    estimated_cost DECIMAL,
    actual_cost DECIMAL,
    duration_seconds INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        vs.id,
        vs.task_type,
        vs.k_threshold,
        vs.total_samples,
        vs.flagged_samples,
        vs.total_samples - vs.flagged_samples AS valid_samples,
        vs.convergence_rounds,
        vs.winner,
        vs.winner_votes,
        (
            SELECT jsonb_object_agg(vote_for, vote_count)
            FROM (
                SELECT vote_for, COUNT(*) as vote_count
                FROM votes
                WHERE session_id = session_uuid AND was_flagged = FALSE
                GROUP BY vote_for
            ) vote_counts
        ) AS vote_distribution,
        (
            SELECT jsonb_object_agg(flag_reason, flag_count)
            FROM (
                SELECT unnest(flag_reasons) as flag_reason, COUNT(*) as flag_count
                FROM votes
                WHERE session_id = session_uuid AND was_flagged = TRUE
                GROUP BY flag_reason
            ) flag_counts
        ) AS flag_distribution,
        vs.estimated_cost,
        vs.actual_cost,
        EXTRACT(EPOCH FROM (vs.completed_at - vs.created_at))::INTEGER AS duration_seconds
    FROM voting_sessions vs
    WHERE vs.id = session_uuid;
END;
$$ LANGUAGE plpgsql;

-- View: Recent voting sessions with summary stats
CREATE OR REPLACE VIEW recent_voting_sessions AS
SELECT 
    vs.id,
    vs.thesis_id,
    vs.task_type,
    vs.k_threshold,
    vs.total_samples,
    vs.flagged_samples,
    vs.convergence_rounds,
    vs.winner_votes,
    vs.estimated_cost,
    vs.actual_cost,
    vs.created_at,
    vs.completed_at,
    EXTRACT(EPOCH FROM (vs.completed_at - vs.created_at))::INTEGER AS duration_seconds,
    (vs.total_samples - vs.flagged_samples)::FLOAT / NULLIF(vs.total_samples, 0) AS valid_rate,
    COUNT(v.id) AS vote_count
FROM voting_sessions vs
LEFT JOIN votes v ON v.session_id = vs.id
GROUP BY vs.id
ORDER BY vs.created_at DESC
LIMIT 100;

COMMENT ON TABLE voting_sessions IS 'Tracks MAKER framework voting sessions for error correction';
COMMENT ON TABLE votes IS 'Individual votes within a voting session';
COMMENT ON TABLE red_flag_stats IS 'Aggregated statistics about red-flagged responses';
COMMENT ON FUNCTION get_voting_session_summary IS 'Get comprehensive summary of a voting session including vote and flag distributions';
