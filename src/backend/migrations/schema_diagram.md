# Database Schema Diagram

## Entity Relationship Overview

```
┌─────────────────┐
│     users       │
├─────────────────┤
│ id (PK)         │──┐
│ email           │  │
│ password_hash   │  │
│ full_name       │  │
│ role            │  │
│ created_at      │  │
│ updated_at      │  │
└─────────────────┘  │
                     │
       ┌─────────────┼───────────────┐
       │             │               │
       ▼             ▼               ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│     api_keys    │ │ refresh_tokens  │ │    projects     │
├─────────────────┤ ├─────────────────┤ ├─────────────────┤
│ id (PK)         │ │ id (PK)         │ │ id (PK)         │
│ user_id (FK)    │ │ user_id (FK)    │ │ user_id (FK)    │
│ name            │ │ token           │ │ name            │
│ key_hash        │ │ expires_at      │ │ description     │
│ last_used       │ │ created_at      │ │ status          │
│ created_at      │ └─────────────────┘ │ created_at      │
│ expires_at      │                     │ updated_at      │
└─────────────────┘                     └─────────────────┘
                                             │
                                             ▼
                                   ┌─────────────────┐
                                   │   recordings    │
                                   ├─────────────────┤
                                   │ id (PK)         │
                                   │ project_id (FK) │
                                   │ user_id (FK)    │
                                   │ filename        │
                                   │ duration        │
                                   │ file_size       │
                                   │ status          │
                                   │ transcription   │
                                   │ created_at      │
                                   │ updated_at      │
                                   └─────────────────┘

┌─────────────────┐
│      tags       │
├─────────────────┤
│ id (PK)         │
│ project_id (FK) │──┐
│ name            │  │
│ color           │  │
│ created_at      │  │
└─────────────────┘  │
                     │
       ┌─────────────┘
       │
       ▼
┌─────────────────┐
│    projects     │
│ (see above)     │
└─────────────────┘
```

## Foreign Key Relationships

### users (parent)
- `api_keys.user_id` → `users.id` (CASCADE)
- `refresh_tokens.user_id` → `users.id` (CASCADE)
- `projects.user_id` → `users.id` (CASCADE)
- `recordings.user_id` → `users.id` (CASCADE)

### projects (parent)
- `recordings.project_id` → `projects.id` (CASCADE)
- `tags.project_id` → `projects.id` (CASCADE)

## Cascade Delete Behavior

When a **user** is deleted:
- All their API keys are deleted
- All their refresh tokens are deleted
- All their projects are deleted
  - All recordings in those projects are deleted
  - All tags on those projects are deleted

When a **project** is deleted:
- All recordings in that project are deleted
- All tags on that project are deleted

## Indexes for Performance

### users table
- `idx_users_email` - Fast authentication lookups
- `idx_users_role` - Role-based queries

### api_keys table
- `idx_api_keys_user_id` - User's API keys
- `idx_api_keys_key_hash` - API key validation
- `idx_api_keys_expires_at` - Expired key cleanup

### refresh_tokens table
- `idx_refresh_tokens_user_id` - User's tokens
- `idx_refresh_tokens_token` - Token validation
- `idx_refresh_tokens_expires_at` - Expired token cleanup

### projects table
- `idx_projects_user_id` - User's projects
- `idx_projects_status` - Status filtering
- `idx_projects_created_at` - Recent projects

### recordings table
- `idx_recordings_project_id` - Project's recordings
- `idx_recordings_user_id` - User's recordings
- `idx_recordings_status` - Status filtering
- `idx_recordings_created_at` - Recent recordings

### tags table
- `idx_tags_project_id` - Project's tags
- `idx_tags_name` - Tag search

## Views

### project_summaries
Aggregates project data with recording statistics:
- Project details
- Owner information
- Recording counts (total, completed, pending)

### user_activity
Aggregates user activity data:
- Project count
- Recording count
- Last recording timestamp
- API key count

## Constraints

### Unique Constraints
- `users.email` - One email per user
- `api_keys.key_hash` - One API key per hash
- `refresh_tokens.token` - One token per value
- `tags(project_id, name)` - One tag name per project

### Check Constraints
- `users.role` - Only 'user', 'admin', 'moderator'
- `projects.status` - Only 'active', 'archived', 'deleted'
- `recordings.status` - Only 'pending', 'processing', 'completed', 'failed'

## Data Types

### UUID
- All primary keys use `gen_random_uuid()`
- Provides globally unique identifiers
- Prevents ID enumeration attacks

### TIMESTAMPTZ
- All timestamps use timezone-aware timestamps
- Stored in UTC
- Automatically converted to client timezone

### VARCHAR
- Email: 255 characters (RFC 5321 limit)
- Name fields: 255 characters
- Token: 500 characters (JWT tokens)

### TEXT
- Unbounded text for descriptions
- Transcription content

### FLOAT
- Duration in seconds (supports milliseconds)

### INTEGER
- File size in bytes (up to 2GB)
