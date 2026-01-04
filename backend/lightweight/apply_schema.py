import asyncio
import os
import asyncpg

async def apply_schema():
    print("Connecting to database...")
    # Use the URL from docker-compose or default to local
    dsn = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/thesis")
    
    try:
        conn = await asyncpg.connect(dsn)
        print("Connected.")
        
        schema_sql = """
        -- Enable UUID extension
        CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

        -- Thesis Table (Update)
        CREATE TABLE IF NOT EXISTS thesis (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            topic TEXT,
            case_study TEXT,
            methodology TEXT,
            objective_store JSONB DEFAULT '{}'::jsonb, -- Central Objective Store
            created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
        );
        
        -- Add column if table exists but column doesn't
        DO $$ 
        BEGIN 
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='thesis' AND column_name='objective_store') THEN 
                ALTER TABLE thesis ADD COLUMN objective_store JSONB DEFAULT '{}'::jsonb; 
            END IF; 
        END $$;

        -- Sources Table
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
        
        -- Objectives Table
        CREATE TABLE IF NOT EXISTS objectives (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            thesis_id UUID REFERENCES thesis(id) ON DELETE CASCADE,
            objective_text TEXT NOT NULL,
            objective_type TEXT NOT NULL, -- 'general' or 'specific'
            objective_number INTEGER, -- 1, 2, 3... (null for general)
            topic TEXT,
            case_study TEXT,
            methodology TEXT,
            validation_status TEXT DEFAULT 'pending',
            validation_score FLOAT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
            UNIQUE(thesis_id, objective_type, objective_number)
        );
        
        -- Users Table
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            username TEXT,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
        );

        -- Workspaces Table
        CREATE TABLE IF NOT EXISTS workspaces (
            workspace_id TEXT PRIMARY KEY,
            owner_user_id TEXT REFERENCES users(user_id) ON DELETE CASCADE,
            name TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
            UNIQUE(owner_user_id)  -- For now, one workspace per user to start
        );

        -- RLS
        ALTER TABLE sources ENABLE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS "Allow all access" ON sources;
        CREATE POLICY "Allow all access" ON sources FOR ALL USING (true);
        
        ALTER TABLE objectives ENABLE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS "Allow all access" ON objectives;
        CREATE POLICY "Allow all access" ON objectives FOR ALL USING (true);
        """
        
        print("Applying schema...")
        await conn.execute(schema_sql)
        print("Schema applied successfully.")
        
        await conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(apply_schema())
