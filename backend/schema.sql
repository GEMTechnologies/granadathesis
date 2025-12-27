-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Thesis Table
CREATE TABLE IF NOT EXISTS thesis (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    topic TEXT NOT NULL,
    student_name TEXT,
    university TEXT DEFAULT 'University of Juba',
    status TEXT DEFAULT 'planning',
    objectives JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Chapters Table
CREATE TABLE IF NOT EXISTS chapters (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    thesis_id UUID REFERENCES thesis(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    chapter_number INTEGER NOT NULL,
    content TEXT,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Sections Table
CREATE TABLE IF NOT EXISTS sections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chapter_id UUID REFERENCES chapters(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    section_number TEXT NOT NULL, -- e.g., "1.1", "1.2"
    content TEXT,
    research_notes TEXT,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Enable Row Level Security (RLS) - Optional but recommended
ALTER TABLE thesis ENABLE ROW LEVEL SECURITY;
ALTER TABLE chapters ENABLE ROW LEVEL SECURITY;
ALTER TABLE sections ENABLE ROW LEVEL SECURITY;

-- Create policies (Allow all for now for development)
CREATE POLICY "Allow all access" ON thesis FOR ALL USING (true);
CREATE POLICY "Allow all access" ON sections FOR ALL USING (true);

-- Sources Table (New)
CREATE TABLE IF NOT EXISTS sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    thesis_id UUID REFERENCES thesis(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    url TEXT,
    type TEXT, -- 'news', 'academic', 'web', 'pdf'
    content TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    source_hash TEXT, -- For deduplication
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

CREATE POLICY "Allow all access" ON sources FOR ALL USING (true);
ALTER TABLE sources ENABLE ROW LEVEL SECURITY;
