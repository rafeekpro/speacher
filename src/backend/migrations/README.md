# Database Migrations

This directory contains PostgreSQL migration scripts for the Speecher application.

## Database Connection

- **Host**: 10.0.0.5
- **Port**: 30432
- **Database**: speacher
- **User**: speacher_user

## Migration Files

### 001_initial_schema.sql

Creates the initial database schema for multi-user authentication and project management:

**Tables:**
- `users` - User accounts with authentication
- `api_keys` - API keys for programmatic access
- `refresh_tokens` - JWT refresh token storage
- `projects` - User projects
- `recordings` - Audio recordings within projects
- `tags` - Tags for organizing projects

**Features:**
- UUID primary keys
- Timestamp tracking (created_at, updated_at)
- Foreign key constraints with CASCADE deletes
- Indexes for performance
- Check constraints for data validation
- Auto-update triggers for updated_at
- Views for common queries
- Default admin user (admin@localhost / Admin123!)

**Indexes:**
- Email lookups for authentication
- Foreign key indexes for joins
- Status and timestamp indexes for filtering
- Unique constraints for data integrity

## Running Migrations

### Option 1: Using PostgreSQL Client

```bash
cd /Users/rla/Projects/Speecher/src/backend
./scripts/run_migration.sh migrations/001_initial_schema.sql
```

### Option 2: Using Docker (Recommended)

```bash
cd /Users/rla/Projects/Speecher/src/backend
./scripts/run_migration_docker.sh migrations/001_initial_schema.sql
```

### Option 3: Manual psql Command

```bash
psql -h 10.0.0.5 -p 30432 -U speacher_user -d speacher -f migrations/001_initial_schema.sql
```

## Verifying Migration

After running the migration, verify tables were created:

```sql
\dt
```

Expected output:
```
          List of relations
 Schema |     Name      | Type  |    Owner
--------+---------------+-------+-------------
 public | api_keys      | table | speacher_user
 public | projects      | table | speacher_user
 public | recordings    | table | speacher_user
 public | refresh_tokens| table | speacher_user
 public | tags          | table | speacher_user
 public | users         | table | speacher_user
```

## Testing the Schema

### Test Default Admin User

```sql
SELECT id, email, full_name, role FROM users WHERE email = 'admin@localhost';
```

### Test Views

```sql
-- Project summaries view
SELECT * FROM project_summaries;

-- User activity view
SELECT * FROM user_activity;
```

## Schema Features

### Auto-Update Timestamps

The `updated_at` column is automatically updated via triggers:

```sql
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

### Cascade Deletes

Foreign keys use `ON DELETE CASCADE` to maintain referential integrity:

- Deleting a user deletes all their projects, recordings, API keys, and tokens
- Deleting a project deletes all its recordings and tags

### Data Validation

Check constraints ensure data integrity:

```sql
CONSTRAINT users_role_check CHECK (role IN ('user', 'admin', 'moderator'))
CONSTRAINT projects_status_check CHECK (status IN ('active', 'archived', 'deleted'))
CONSTRAINT recordings_status_check CHECK (status IN ('pending', 'processing', 'completed', 'failed'))
```

### Idempotent Inserts

The default admin user insert uses `ON CONFLICT` to avoid duplicates:

```sql
INSERT INTO users (email, password_hash, full_name, role)
VALUES (...)
ON CONFLICT (email) DO NOTHING;
```

## Password Hashing

The default admin password uses bcrypt (cost factor: 12):

```
Password: Admin123!
Hash: $2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzW5qtGLJi
```

To generate new bcrypt hashes, you can use Python:

```python
import bcrypt
password = "your_password".encode('utf-8')
hashed = bcrypt.hashpw(password, bcrypt.gensalt(rounds=12))
print(hashed.decode('utf-8'))
```

## Rollback

To rollback the migration (drop all tables):

```sql
DROP VIEW IF EXISTS user_activity CASCADE;
DROP VIEW IF EXISTS project_summaries CASCADE;
DROP TABLE IF EXISTS tags CASCADE;
DROP TABLE IF EXISTS recordings CASCADE;
DROP TABLE IF EXISTS projects CASCADE;
DROP TABLE IF EXISTS refresh_tokens CASCADE;
DROP TABLE IF EXISTS api_keys CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;
```

## Security Notes

- All passwords are stored as bcrypt hashes (cost factor: 12)
- API keys are stored as SHA-256 hashes
- Never store plaintext passwords or API keys
- Use prepared statements to prevent SQL injection
- Implement rate limiting on authentication endpoints

## Future Migrations

Naming convention: `###_description.sql`

Example:
```
002_add_user_preferences.sql
003_add_recording_metadata.sql
004_add_project_sharing.sql
```

Each migration should be:
- Idempotent (can be run multiple times safely)
- Reversible (include rollback instructions in comments)
- Documented (describe changes in header comments)
- Tested (verify on development database first)
