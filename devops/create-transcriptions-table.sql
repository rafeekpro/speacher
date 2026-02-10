-- Create transcriptions table with nullable foreign keys
DO $$
BEGIN
    -- Create enum type if not exists
    CREATE TYPE transcription_status AS ENUM ('pending', 'processing', 'completed', 'failed', 'cancelled');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

CREATE TABLE IF NOT EXISTS transcriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    audio_file_id UUID,
    user_id UUID,
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
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_transcriptions_created_at ON transcriptions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_transcriptions_status ON transcriptions(status);
CREATE INDEX IF NOT EXISTS idx_transcriptions_text_search ON transcriptions USING gin(to_tsvector('english', text));

-- Grant permissions
GRANT ALL PRIVILEGES ON TABLE transcriptions TO speacher_user;
GRANT USAGE ON SCHEMA public TO speacher_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO speacher_user;

SELECT 'Transcriptions table created successfully!' AS result;
