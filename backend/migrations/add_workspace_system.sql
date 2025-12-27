-- Migration: Workspace System for Users, Folders, and Files
-- Created: 2025-11-30
-- Description: Adds tables for user workspaces, folders, files, and file operations

-- Users Table (if not exists)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    full_name TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Workspaces Table (One per user)
CREATE TABLE IF NOT EXISTS workspaces (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL DEFAULT 'My Workspace',
    root_path TEXT NOT NULL, -- Filesystem path
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    UNIQUE(user_id)
);

-- Folders Table (Hierarchical structure)
CREATE TABLE IF NOT EXISTS folders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    parent_folder_id UUID REFERENCES folders(id) ON DELETE CASCADE, -- NULL for root folders
    name VARCHAR(255) NOT NULL,
    path TEXT NOT NULL, -- Full path from workspace root
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    created_by UUID REFERENCES users(id),
    UNIQUE(workspace_id, parent_folder_id, name) -- Prevent duplicate folder names in same parent
);

-- Files Table
CREATE TABLE IF NOT EXISTS workspace_files (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    folder_id UUID REFERENCES folders(id) ON DELETE SET NULL, -- NULL if in workspace root
    name VARCHAR(255) NOT NULL,
    original_name VARCHAR(255) NOT NULL, -- Original filename on upload
    file_path TEXT NOT NULL, -- Full filesystem path
    file_type VARCHAR(50), -- 'document', 'pdf', 'image', 'data', etc.
    mime_type VARCHAR(100),
    file_size BIGINT, -- Size in bytes
    content_hash TEXT, -- For deduplication
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    created_by UUID REFERENCES users(id),
    UNIQUE(workspace_id, folder_id, name) -- Prevent duplicate file names in same folder
);

-- Projects Table (Special type of folder/workspace item)
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    folder_id UUID REFERENCES folders(id) ON DELETE SET NULL, -- Can be inside a folder
    name VARCHAR(255) NOT NULL,
    project_type VARCHAR(50) NOT NULL, -- 'thesis', 'essay', 'article', 'journal', 'report', etc.
    description TEXT,
    status VARCHAR(50) DEFAULT 'active',
    metadata JSONB DEFAULT '{}'::jsonb, -- Store project-specific settings
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    created_by UUID REFERENCES users(id)
);

-- File Operations Log (for audit trail)
CREATE TABLE IF NOT EXISTS file_operations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    file_id UUID REFERENCES workspace_files(id) ON DELETE SET NULL,
    folder_id UUID REFERENCES folders(id) ON DELETE SET NULL,
    operation_type VARCHAR(50) NOT NULL, -- 'create', 'move', 'rename', 'delete', 'upload', 'download'
    old_path TEXT, -- For move/rename operations
    new_path TEXT,
    performed_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_workspaces_user_id ON workspaces(user_id);
CREATE INDEX IF NOT EXISTS idx_folders_workspace_id ON folders(workspace_id);
CREATE INDEX IF NOT EXISTS idx_folders_parent_id ON folders(parent_folder_id);
CREATE INDEX IF NOT EXISTS idx_files_workspace_id ON workspace_files(workspace_id);
CREATE INDEX IF NOT EXISTS idx_files_folder_id ON workspace_files(folder_id);
CREATE INDEX IF NOT EXISTS idx_projects_workspace_id ON projects(workspace_id);
CREATE INDEX IF NOT EXISTS idx_file_operations_workspace_id ON file_operations(workspace_id);
CREATE INDEX IF NOT EXISTS idx_file_operations_file_id ON file_operations(file_id);

-- Enable Row Level Security
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE folders ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspace_files ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE file_operations ENABLE ROW LEVEL SECURITY;

-- Create policies (Allow all for now - should be user-specific in production)
CREATE POLICY "Allow all access" ON users FOR ALL USING (true);
CREATE POLICY "Allow all access" ON workspaces FOR ALL USING (true);
CREATE POLICY "Allow all access" ON folders FOR ALL USING (true);
CREATE POLICY "Allow all access" ON workspace_files FOR ALL USING (true);
CREATE POLICY "Allow all access" ON projects FOR ALL USING (true);
CREATE POLICY "Allow all access" ON file_operations FOR ALL USING (true);

-- Create default upload folder structure helper function
CREATE OR REPLACE FUNCTION ensure_upload_folder(workspace_uuid UUID, user_uuid UUID)
RETURNS UUID AS $$
DECLARE
    upload_folder_id UUID;
BEGIN
    -- Check if uploads folder exists in workspace root
    SELECT id INTO upload_folder_id
    FROM folders
    WHERE workspace_id = workspace_uuid
      AND parent_folder_id IS NULL
      AND name = 'uploads';
    
    -- Create if doesn't exist
    IF upload_folder_id IS NULL THEN
        INSERT INTO folders (workspace_id, parent_folder_id, name, path, created_by)
        VALUES (workspace_uuid, NULL, 'uploads', 'uploads', user_uuid)
        RETURNING id INTO upload_folder_id;
    END IF;
    
    RETURN upload_folder_id;
END;
$$ LANGUAGE plpgsql;

















