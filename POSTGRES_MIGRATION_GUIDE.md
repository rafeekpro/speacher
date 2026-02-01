# PostgreSQL Migration Guide

## Overview

The backend has been refactored to use PostgreSQL instead of MongoDB for storing transcriptions. This provides better data integrity, relationships, and consistency with the existing API keys storage.

## Changes Made

### 1. New Files Created

- **`/src/backend/transcriptions_db.py`**
  - SQLAlchemy models for transcriptions table
  - TranscriptionManager class for database operations
  - Functions for CRUD operations on transcriptions
  - Statistics aggregation

- **`/docker/make-transcription-nullable.sql`**
  - Migration script to recreate transcriptions table with nullable foreign keys
  - Allows transcriptions without requiring audio_file_id and user_id
  - Recreates indexes and constraints

### 2. Modified Files

- **`/src/backend/main.py`**
  - Removed MongoDB imports (bson, pymongo)
  - Added PostgreSQL transcription manager import
  - Updated `/api/transcribe` to save to PostgreSQL
  - Updated `/api/history` to fetch from PostgreSQL
  - Updated `/api/transcription/{id}` to fetch from PostgreSQL
  - Updated `DELETE /api/transcription/{id}` to delete from PostgreSQL
  - Updated `/api/stats` to use PostgreSQL aggregation
  - Updated `/db/health` to check PostgreSQL connection

## Migration Steps

### Step 1: Run Database Migration

Apply the SQL migration to make the transcriptions table work without requiring audio_file_id and user_id:

```bash
# If using docker compose
docker compose exec postgres psql -U speacher_user -d speacher -f /docker/make-transcription-nullable.sql

# If using direct PostgreSQL access
psql -h 10.0.0.5 -p 30432 -U speacher_user -d speacher -f docker/make-transcription-nullable.sql
```

### Step 2: Install Python Dependencies

The new code uses SQLAlchemy. Make sure it's installed:

```bash
# If using uv
uv pip install sqlalchemy

# If using pip
pip install sqlalchemy
```

### Step 3: Restart the Backend

```bash
# Restart the backend service
docker compose restart backend

# Or rebuild if needed
docker compose up -d --build backend
```

### Step 4: Verify the Migration

Test that the endpoints work correctly:

1. **Health Check**
   ```bash
   curl http://localhost:8000/db/health
   # Should return: {"status":"healthy","database":"PostgreSQL connected"}
   ```

2. **Create a Transcription**
   - Upload an audio file through the UI
   - Check that it saves to PostgreSQL

3. **View History**
   - Go to the history page
   - Transcriptions should persist across page refreshes

4. **Check Database**
   ```bash
   docker compose exec postgres psql -U speacher_user -d speacher -c "SELECT id, text, language, created_at FROM transcriptions ORDER BY created_at DESC LIMIT 5;"
   ```

## Database Schema

### Transcriptions Table

```sql
CREATE TABLE transcriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    audio_file_id UUID REFERENCES audio_files(id) ON DELETE CASCADE,  -- NULLABLE
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,                -- NULLABLE
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
```

### Metadata Field

The `metadata` JSONB field stores:
- `filename`: Original filename
- `provider`: Cloud provider (aws/azure/gcp)
- `enable_diarization`: Whether speaker diarization was enabled
- `max_speakers`: Maximum number of speakers
- `duration`: Audio duration in seconds
- `cost_estimate`: Estimated transcription cost
- `file_size`: File size in bytes
- `speakers`: Array of speaker segments with timestamps

## API Compatibility

The refactored endpoints maintain backward compatibility with the frontend:

- **Response format** is identical to the MongoDB implementation
- **Field names** match the expected format
- **Timestamps** are returned in ISO format
- **UUIDs** are returned as strings

## Future Improvements

### 1. Add User Authentication

Currently, `user_id` is NULL. To add user authentication:

1. Create a default user or use JWT authentication
2. Update `save_transcription()` to include `user_id`
3. Filter history by user

### 2. Add Audio File Tracking

Currently, `audio_file_id` is NULL. To track audio files:

1. Create audio file records on upload
2. Link transcriptions to audio files
3. Enable audio file management

### 3. Add Word Timestamps

The `word_timestamps` table exists but isn't populated yet. To enable:

1. Extract word-level timestamps from transcription results
2. Store in `word_timestamps` table
3. Add API endpoints for word-level data

## Troubleshooting

### Error: "relation 'transcriptions' does not exist"

**Solution**: Run the migration script:
```bash
docker compose exec postgres psql -U speacher_user -d speacher -f /docker/make-transcription-nullable.sql
```

### Error: "null value in column 'audio_file_id' violates not-null constraint"

**Solution**: The migration script should make these columns nullable. If you still see this error, verify the migration ran successfully.

### Error: "SQLAlchemy module not found"

**Solution**: Install SQLAlchemy:
```bash
pip install sqlalchemy
# or
uv pip install sqlalchemy
```

### Transcriptions not persisting

**Check**:
1. PostgreSQL is running: `docker compose ps`
2. Database connection is valid: `curl http://localhost:8000/db/health`
3. Backend logs: `docker compose logs backend`
4. Database contains data: `docker compose exec postgres psql -U speacher_user -d speacher -c "SELECT COUNT(*) FROM transcriptions;"`

## Rollback Plan

If you need to rollback to MongoDB:

1. Restore the original `main.py` from git history
2. Ensure MongoDB is configured and running
3. Restart the backend

```bash
git checkout HEAD~1 src/backend/main.py
docker compose restart backend
```

## Performance Considerations

### Advantages of PostgreSQL

1. **ACID Compliance**: Guaranteed data integrity
2. **Foreign Keys**: Enforced relationships between tables
3. **JSONB**: Efficient storage and querying of metadata
4. **Full-Text Search**: Built-in text search capabilities
5. **Indexes**: Optimized queries with proper indexes
6. **Scalability**: Better for large datasets

### Query Optimization

Key indexes created:
- `idx_transcriptions_user_id`: Fast user lookups
- `idx_transcriptions_audio_file_id`: Fast audio file lookups
- `idx_transcriptions_status`: Filter by status
- `idx_transcriptions_created_at`: Sort by creation time
- `idx_transcriptions_text_search`: Full-text search on transcript text

## Data Migration from MongoDB

If you have existing data in MongoDB that you want to migrate:

```python
# Migration script (run once)
import pymongo
from backend.transcriptions_db import transcription_manager

# Connect to MongoDB
mongo_client = pymongo.MongoClient("mongodb://localhost:27017/")
mongo_collection = mongo_client["speacher"]["transcriptions"]

# Fetch all documents
docs = mongo_collection.find()

# Migrate to PostgreSQL
for doc in docs:
    transcription_manager.save_transcription(
        filename=doc.get("filename", ""),
        provider=doc.get("provider", "unknown"),
        language=doc.get("language", "en"),
        transcript=doc.get("transcript", ""),
        speakers=doc.get("speakers", []),
        enable_diarization=doc.get("enable_diarization", True),
        max_speakers=doc.get("max_speakers", 4),
        duration=doc.get("duration", 0.0),
        cost_estimate=doc.get("cost_estimate", 0.0),
        file_size=doc.get("file_size", 0),
        audio_file_id=None,
        user_id=None,
    )

print("Migration complete!")
```

## Support

For issues or questions:
1. Check the logs: `docker compose logs backend`
2. Verify database connectivity: `curl http://localhost:8000/db/health`
3. Check database tables: `docker compose exec postgres psql -U speacher_user -d speacher -c "\dt speecher.*"`
