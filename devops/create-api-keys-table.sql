-- Create api_keys table in PostgreSQL
CREATE TABLE IF NOT EXISTS api_keys (
    provider VARCHAR(50) PRIMARY KEY,
    keys JSONB DEFAULT '{}'::jsonb,
    enabled BOOLEAN DEFAULT TRUE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Grant permissions
GRANT ALL PRIVILEGES ON TABLE api_keys TO speacher_user;

SELECT 'api_keys table created successfully!' AS result;
