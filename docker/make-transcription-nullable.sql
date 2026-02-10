-- Migration script to make transcriptions table work without requiring audio_file_id and user_id
-- This allows transcriptions to be saved independently for now

-- Drop the existing transcriptions table and recreate with nullable foreign keys
-- WARNING: This will delete existing transcription data

DROP TABLE IF EXISTS word_timestamps CASCADE;
DROP TABLE IF EXISTS transcriptions CASCADE;

-- Create transcriptions table with nullable foreign keys
CREATE TABLE IF NOT EXISTS transcriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    audio_file_id UUID REFERENCES audio_files(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
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
    CONSTRAINT valid_confidence CHECK (confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1))
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
    CONSTRAINT valid_word_confidence CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1))
);

-- Recreate indexes
CREATE INDEX IF NOT EXISTS idx_transcriptions_user_id ON transcriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_transcriptions_audio_file_id ON transcriptions(audio_file_id);
CREATE INDEX IF NOT EXISTS idx_transcriptions_status ON transcriptions(status);
CREATE INDEX IF NOT EXISTS idx_transcriptions_created_at ON transcriptions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_word_timestamps_transcription_id ON word_timestamps(transcription_id);
CREATE INDEX IF NOT EXISTS idx_word_timestamps_position ON word_timestamps(transcription_id, position);

-- Full text search index
CREATE INDEX IF NOT EXISTS idx_transcriptions_text_search ON transcriptions USING gin(to_tsvector('english', text));

-- Add comments
COMMENT ON TABLE transcriptions IS 'Transcription results for audio files (audio_file_id and user_id are nullable)';
COMMENT ON TABLE word_timestamps IS 'Word-level timing information for transcriptions';
