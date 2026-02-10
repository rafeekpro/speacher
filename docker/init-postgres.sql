-- PostgreSQL initialization script for Speecher development environment
-- This script runs when the PostgreSQL container is first created

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS speecher;
CREATE SCHEMA IF NOT EXISTS audit;

-- Set default schema search path
SET search_path TO speecher, public;

-- Create enum types
CREATE TYPE user_role AS ENUM ('admin', 'user', 'guest');
CREATE TYPE audio_status AS ENUM ('pending', 'processing', 'completed', 'failed');
CREATE TYPE transcription_status AS ENUM ('pending', 'processing', 'completed', 'failed', 'cancelled');

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role user_role DEFAULT 'user',
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create audio_files table
CREATE TABLE IF NOT EXISTS audio_files (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    filename VARCHAR(500) NOT NULL,
    original_filename VARCHAR(500),
    file_size BIGINT,
    duration_seconds FLOAT,
    format VARCHAR(50),
    sample_rate INTEGER,
    channels INTEGER,
    bitrate INTEGER,
    storage_path TEXT,
    storage_provider VARCHAR(50) DEFAULT 'local',
    status audio_status DEFAULT 'pending',
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}'::jsonb,
    CONSTRAINT valid_file_size CHECK (file_size >= 0),
    CONSTRAINT valid_duration CHECK (duration_seconds >= 0)
);

-- Create transcriptions table
CREATE TABLE IF NOT EXISTS transcriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    audio_file_id UUID NOT NULL REFERENCES audio_files(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    text TEXT,
    language VARCHAR(10) DEFAULT 'en',
    confidence_score FLOAT,
    word_count INTEGER,
    status transcription_status DEFAULT 'pending',
    engine VARCHAR(50) DEFAULT 'whisper',
    engine_version VARCHAR(50),
    processing_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}'::jsonb,
    CONSTRAINT valid_confidence CHECK (confidence_score >= 0 AND confidence_score <= 1)
);

-- Create word_timestamps table for detailed transcription data
CREATE TABLE IF NOT EXISTS word_timestamps (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    transcription_id UUID NOT NULL REFERENCES transcriptions(id) ON DELETE CASCADE,
    word VARCHAR(255) NOT NULL,
    start_time FLOAT NOT NULL,
    end_time FLOAT NOT NULL,
    confidence FLOAT,
    speaker_id VARCHAR(50),
    position INTEGER NOT NULL,
    CONSTRAINT valid_times CHECK (start_time >= 0 AND end_time > start_time),
    CONSTRAINT valid_word_confidence CHECK (confidence >= 0 AND confidence <= 1)
);

-- Create sessions table for user sessions
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(500) UNIQUE NOT NULL,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true
);

-- Create api_keys table
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    permissions JSONB DEFAULT '[]'::jsonb,
    rate_limit INTEGER DEFAULT 1000,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true
);

-- Create audit log table
CREATE TABLE IF NOT EXISTS audit.activity_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES speecher.users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(100),
    entity_id UUID,
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create indexes for better performance
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_created_at ON users(created_at DESC);

CREATE INDEX idx_audio_files_user_id ON audio_files(user_id);
CREATE INDEX idx_audio_files_status ON audio_files(status);
CREATE INDEX idx_audio_files_uploaded_at ON audio_files(uploaded_at DESC);

CREATE INDEX idx_transcriptions_user_id ON transcriptions(user_id);
CREATE INDEX idx_transcriptions_audio_file_id ON transcriptions(audio_file_id);
CREATE INDEX idx_transcriptions_status ON transcriptions(status);
CREATE INDEX idx_transcriptions_created_at ON transcriptions(created_at DESC);

CREATE INDEX idx_word_timestamps_transcription_id ON word_timestamps(transcription_id);
CREATE INDEX idx_word_timestamps_position ON word_timestamps(transcription_id, position);

CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_token ON sessions(token);
CREATE INDEX idx_sessions_expires_at ON sessions(expires_at);

CREATE INDEX idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX idx_api_keys_key_hash ON api_keys(key_hash);

CREATE INDEX idx_activity_log_user_id ON audit.activity_log(user_id);
CREATE INDEX idx_activity_log_created_at ON audit.activity_log(created_at DESC);
CREATE INDEX idx_activity_log_entity ON audit.activity_log(entity_type, entity_id);

-- Full text search indexes
CREATE INDEX idx_transcriptions_text_search ON transcriptions USING gin(to_tsvector('english', text));

-- Create update timestamp trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply update timestamp trigger to tables
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create function for cleaning expired sessions
CREATE OR REPLACE FUNCTION clean_expired_sessions()
RETURNS void AS $$
BEGIN
    UPDATE sessions 
    SET is_active = false 
    WHERE expires_at < NOW() AND is_active = true;
    
    DELETE FROM sessions 
    WHERE expires_at < NOW() - INTERVAL '30 days';
END;
$$ LANGUAGE plpgsql;

-- Create initial admin user (password: admin123 - should be changed immediately)
INSERT INTO users (email, username, password_hash, full_name, role, is_active, is_verified)
VALUES (
    'admin@speecher.local',
    'admin',
    crypt('admin123', gen_salt('bf', 12)),
    'System Administrator',
    'admin',
    true,
    true
) ON CONFLICT (email) DO NOTHING;

-- Create test database for testing
CREATE DATABASE speecher_test WITH TEMPLATE speecher_dev;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE speecher_dev TO speecher;
GRANT ALL PRIVILEGES ON DATABASE speecher_test TO speecher;
GRANT ALL PRIVILEGES ON SCHEMA speecher TO speecher;
GRANT ALL PRIVILEGES ON SCHEMA audit TO speecher;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA speecher TO speecher;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA audit TO speecher;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA speecher TO speecher;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA audit TO speecher;

-- Add comments for documentation
COMMENT ON TABLE users IS 'User accounts for the Speecher application';
COMMENT ON TABLE audio_files IS 'Uploaded audio files for transcription';
COMMENT ON TABLE transcriptions IS 'Transcription results for audio files';
COMMENT ON TABLE word_timestamps IS 'Word-level timing information for transcriptions';
COMMENT ON TABLE sessions IS 'User authentication sessions';
COMMENT ON TABLE api_keys IS 'API keys for programmatic access';
COMMENT ON TABLE audit.activity_log IS 'Audit trail of user activities';

-- Notification for successful initialization
DO $$
BEGIN
    RAISE NOTICE 'PostgreSQL initialization completed successfully for Speecher';
    RAISE NOTICE 'Default admin user created: admin@speecher.local / admin123';
    RAISE NOTICE 'Please change the admin password immediately!';
END $$;