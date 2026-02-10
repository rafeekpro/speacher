-- Migration: 001_initial_schema.sql
-- Description: Initial schema for multi-user authentication and project management
-- Created: 2026-02-02T00:00:00Z

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- USERS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'user',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT users_role_check CHECK (role IN ('user', 'admin', 'moderator'))
);

COMMENT ON TABLE users IS 'User accounts with authentication and authorization';
COMMENT ON COLUMN users.id IS 'Unique user identifier (UUID)';
COMMENT ON COLUMN users.email IS 'User email address (unique)';
COMMENT ON COLUMN users.password_hash IS 'Bcrypt hashed password';
COMMENT ON COLUMN users.full_name IS 'User full name';
COMMENT ON COLUMN users.role IS 'User role: user, admin, or moderator';
COMMENT ON COLUMN users.created_at IS 'Account creation timestamp';
COMMENT ON COLUMN users.updated_at IS 'Last update timestamp';

-- Index for email lookups (authentication)
CREATE INDEX idx_users_email ON users(email);
-- Index for role-based queries
CREATE INDEX idx_users_role ON users(role);

-- ============================================================================
-- DEFAULT ADMIN USER
-- ============================================================================
-- Password: Admin123! (bcrypt hash)
INSERT INTO users (email, password_hash, full_name, role)
VALUES (
    'admin@speecher.local',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzW5qtGLJi',
    'System Administrator',
    'admin'
)
ON CONFLICT (email) DO NOTHING;

-- ============================================================================
-- API KEYS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255),
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    last_used TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ
);

COMMENT ON TABLE api_keys IS 'API keys for programmatic access';
COMMENT ON COLUMN api_keys.id IS 'Unique API key identifier';
COMMENT ON COLUMN api_keys.user_id IS 'Owner user ID';
COMMENT ON COLUMN api_keys.name IS 'Friendly name for the API key';
COMMENT ON COLUMN api_keys.key_hash IS 'SHA-256 hash of the API key';
COMMENT ON COLUMN api_keys.last_used IS 'Last usage timestamp';
COMMENT ON COLUMN api_keys.created_at IS 'Key creation timestamp';
COMMENT ON COLUMN api_keys.expires_at IS 'Key expiration timestamp (NULL = never)';

-- Indexes for API key lookups
CREATE INDEX idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX idx_api_keys_key_hash ON api_keys(key_hash);
CREATE INDEX idx_api_keys_expires_at ON api_keys(expires_at) WHERE expires_at IS NOT NULL;

-- ============================================================================
-- REFRESH TOKENS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(500) UNIQUE NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE refresh_tokens IS 'JWT refresh token storage for authentication';
COMMENT ON COLUMN refresh_tokens.id IS 'Unique token identifier';
COMMENT ON COLUMN refresh_tokens.user_id IS 'Owner user ID';
COMMENT ON COLUMN refresh_tokens.token IS 'JWT refresh token';
COMMENT ON COLUMN refresh_tokens.expires_at IS 'Token expiration timestamp';
COMMENT ON COLUMN refresh_tokens.created_at IS 'Token issuance timestamp';

-- Indexes for token lookups and cleanup
CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_token ON refresh_tokens(token);
CREATE INDEX idx_refresh_tokens_expires_at ON refresh_tokens(expires_at);

-- ============================================================================
-- PROJECTS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT projects_status_check CHECK (status IN ('active', 'archived', 'deleted'))
);

COMMENT ON TABLE projects IS 'User projects for organizing recordings';
COMMENT ON COLUMN projects.id IS 'Unique project identifier';
COMMENT ON COLUMN projects.user_id IS 'Owner user ID';
COMMENT ON COLUMN projects.name IS 'Project name';
COMMENT ON COLUMN projects.description IS 'Project description';
COMMENT ON COLUMN projects.status IS 'Project status: active, archived, or deleted';
COMMENT ON COLUMN projects.created_at IS 'Project creation timestamp';
COMMENT ON COLUMN projects.updated_at IS 'Last update timestamp';

-- Indexes for project queries
CREATE INDEX idx_projects_user_id ON projects(user_id);
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_projects_created_at ON projects(created_at DESC);

-- ============================================================================
-- RECORDINGS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS recordings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    duration FLOAT,
    file_size INTEGER,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    transcription TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT recordings_status_check CHECK (status IN ('pending', 'processing', 'completed', 'failed'))
);

COMMENT ON TABLE recordings IS 'Audio recordings within projects';
COMMENT ON COLUMN recordings.id IS 'Unique recording identifier';
COMMENT ON COLUMN recordings.project_id IS 'Parent project ID';
COMMENT ON COLUMN recordings.user_id IS 'Owner user ID';
COMMENT ON COLUMN recordings.filename IS 'Audio filename';
COMMENT ON COLUMN recordings.duration IS 'Audio duration in seconds';
COMMENT ON COLUMN recordings.file_size IS 'File size in bytes';
COMMENT ON COLUMN recordings.status IS 'Processing status: pending, processing, completed, or failed';
COMMENT ON COLUMN recordings.transcription IS 'Transcribed text content';
COMMENT ON COLUMN recordings.created_at IS 'Recording upload timestamp';
COMMENT ON COLUMN recordings.updated_at IS 'Last update timestamp';

-- Indexes for recording queries
CREATE INDEX idx_recordings_project_id ON recordings(project_id);
CREATE INDEX idx_recordings_user_id ON recordings(user_id);
CREATE INDEX idx_recordings_status ON recordings(status);
CREATE INDEX idx_recordings_created_at ON recordings(created_at DESC);

-- ============================================================================
-- TAGS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    color VARCHAR(50),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT tags_unique_project_name UNIQUE (project_id, name)
);

COMMENT ON TABLE tags IS 'Tags for organizing and categorizing projects';
COMMENT ON COLUMN tags.id IS 'Unique tag identifier';
COMMENT ON COLUMN tags.project_id IS 'Parent project ID';
COMMENT ON COLUMN tags.name IS 'Tag name';
COMMENT ON COLUMN tags.color IS 'Tag color for UI display';
COMMENT ON COLUMN tags.created_at IS 'Tag creation timestamp';

-- Indexes for tag queries
CREATE INDEX idx_tags_project_id ON tags(project_id);
CREATE INDEX idx_tags_name ON tags(name);

-- ============================================================================
-- FUNCTIONS AND TRIGGERS FOR UPDATED_AT
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_projects_updated_at
    BEFORE UPDATE ON projects
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_recordings_updated_at
    BEFORE UPDATE ON recordings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- View for project summaries with recording counts
CREATE OR REPLACE VIEW project_summaries AS
SELECT
    p.id,
    p.user_id,
    p.name,
    p.description,
    p.status,
    p.created_at,
    p.updated_at,
    u.email as user_email,
    u.full_name as user_full_name,
    COUNT(r.id) as recording_count,
    COUNT(r.id) FILTER (WHERE r.status = 'completed') as completed_recordings,
    COUNT(r.id) FILTER (WHERE r.status = 'pending') as pending_recordings
FROM projects p
LEFT JOIN users u ON p.user_id = u.id
LEFT JOIN recordings r ON p.id = r.project_id
GROUP BY p.id, u.email, u.full_name;

COMMENT ON VIEW project_summaries IS 'Project overview with recording statistics';

-- View for user activity
CREATE OR REPLACE VIEW user_activity AS
SELECT
    u.id,
    u.email,
    u.full_name,
    COUNT(DISTINCT p.id) as project_count,
    COUNT(DISTINCT r.id) as recording_count,
    MAX(r.created_at) as last_recording_at,
    COUNT(DISTINCT ak.id) as api_key_count
FROM users u
LEFT JOIN projects p ON u.id = p.user_id
LEFT JOIN recordings r ON u.id = r.user_id
LEFT JOIN api_keys ak ON u.id = ak.user_id
GROUP BY u.id, u.email, u.full_name;

COMMENT ON VIEW user_activity IS 'User activity summary with project and recording counts';

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================
