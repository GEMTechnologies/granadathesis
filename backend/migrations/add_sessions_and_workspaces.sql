-- Migration: Add Users, Sessions, and Workspace URL tracking
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users Table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT UNIQUE NOT NULL,  -- External user ID (e.g., 'user-1')
    username TEXT,
    email TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Sessions Table
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id TEXT UNIQUE NOT NULL,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    workspace_id TEXT,  -- References workspace name/ID
    session_url TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Workspaces Table (enhanced with URL tracking)
CREATE TABLE IF NOT EXISTS workspaces (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id TEXT UNIQUE NOT NULL,  -- The workspace identifier (e.g., 'default', 'my-thesis')
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name TEXT,
    description TEXT,
    filesystem_path TEXT NOT NULL,
    workspace_url TEXT NOT NULL,
    shareable_url TEXT,
    session_id TEXT REFERENCES sessions(session_id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- User Workspaces Junction Table
CREATE TABLE IF NOT EXISTS user_workspaces (
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    PRIMARY KEY (user_id, workspace_id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_sessions_session_id ON sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_workspaces_workspace_id ON workspaces(workspace_id);
CREATE INDEX IF NOT EXISTS idx_workspaces_user_id ON workspaces(user_id);
CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id);

-- Row Level Security
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_workspaces ENABLE ROW LEVEL SECURITY;

-- Policies (Allow all for development)
CREATE POLICY "Allow all access" ON users FOR ALL USING (true);
CREATE POLICY "Allow all access" ON sessions FOR ALL USING (true);
CREATE POLICY "Allow all access" ON workspaces FOR ALL USING (true);
CREATE POLICY "Allow all access" ON user_workspaces FOR ALL USING (true);

-- Insert default dummy user
INSERT INTO users (user_id, username, email) 
VALUES ('user-1', 'default-user', 'user@example.com')
ON CONFLICT (user_id) DO NOTHING;

















