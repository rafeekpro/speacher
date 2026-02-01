# AWS access_key_id Migration Guide

## Issue #28: Fix AWS access_key_id encryption bug

### Problem

The `access_key_id` field for AWS provider was incorrectly encrypted because it contained the word "key" in its name. This caused AWS authentication to fail since AWS received the encrypted string instead of the actual access key ID.

### Solution

1. **Fix encryption logic** (Stream A): Remove "key" from sensitive keywords list in `src/backend/api_keys.py`
2. **Migrate existing data** (Stream C): Run migration script to decrypt any encrypted `access_key_id` values

## Migration Script

### Location

`scripts/migrate_aws_access_key_id.py`

### Features

- **Dry-run mode**: Test without making changes
- **Encrypted value detection**: Checks for Fernet prefix ("gAAAAA")
- **Safe migration**: Uses database transactions and error handling
- **Detailed reporting**: Shows what was changed
- **Database URL flexibility**: Supports environment variable or argument

### Prerequisites

1. **Stream A must be complete**: The encryption logic in `api_keys.py` must be fixed first
2. **Database access**: Need valid DATABASE_URL environment variable
3. **Backup recommended**: Always backup database before migration

### Usage

#### Development Environment

```bash
# 1. Set database URL
export DATABASE_URL="postgresql://user:pass@host:port/database"

# 2. Test with dry-run (RECOMMENDED FIRST)
docker compose run --rm backend python scripts/migrate_aws_access_key_id.py --dry-run

# 3. If dry-run looks good, apply migration
docker compose run --rm backend python scripts/migrate_aws_access_key_id.py
```

#### Production Environment

```bash
# 1. Backup database first!
pg_dump -U user -h host database > backup_before_migration.sql

# 2. Set database URL
export DATABASE_URL="postgresql://user:pass@production-host:5432/database"

# 3. Test with dry-run
docker compose run --rm backend python scripts/migrate_aws_access_key_id.py --dry-run

# 4. Review dry-run output carefully

# 5. Apply migration
docker compose run --rm backend python scripts/migrate_aws_access_key_id.py

# 6. Verify migration was successful
docker compose run --rm backend python scripts/migrate_aws_access_key_id.py --dry-run
# Should show 0 encrypted access_key_ids

# 7. Test AWS functionality
# Verify S3 upload works with stored credentials
```

### Expected Output

#### Successful Migration (Dry Run)

```
======================================================================
AWS access_key_id Migration Script
======================================================================
Database URL: postgresql://user:pass@host:port/db
Dry Run: True

access_key_id is not encrypted: AKIAIOSFODNN...

======================================================================
Migration Summary
======================================================================
AWS credentials found: 1
Encrypted access_key_ids: 0
Migrated: 0
Skipped: 1
Errors: 0
```

#### Successful Migration (Actual)

```
======================================================================
AWS access_key_id Migration Script
======================================================================
Database URL: postgresql://user:pass@host:port/db
Dry Run: False

Successfully migrated access_key_id: AKIAIOSFODNN...

======================================================================
Migration Summary
======================================================================
AWS credentials found: 1
Encrypted access_key_ids: 1
Migrated: 1
Skipped: 0
Errors: 0
```

### How It Works

1. **Fetch AWS credentials**: Queries database for AWS provider credentials
2. **Detect encryption**: Checks if `access_key_id` starts with "gAAAAA" (Fernet prefix)
3. **Decrypt value**: Uses existing cipher suite to decrypt the value
4. **Update database**: Saves credentials with unencrypted `access_key_id`
5. **Report results**: Shows what was changed

### Error Handling

The script handles various error conditions:

- **No credentials found**: Reports and exits cleanly
- **Invalid format**: Skips records with invalid data
- **Decryption failures**: Logs errors and continues
- **Database errors**: Reports and exits with error code

### Exit Codes

- `0`: Success (all migrations completed or nothing to migrate)
- `1`: Error occurred during migration
- `2`: Encrypted access_key_ids found (dry-run mode)

### Verification

After migration, verify:

1. **Dry-run shows 0 encrypted**: Run again with `--dry-run` to confirm no encrypted values remain
2. **AWS functionality works**: Test S3 upload with stored credentials
3. **No regressions**: Verify Azure and GCP providers still work

### Rollback

If migration causes issues:

1. Restore database from backup
2. Investigate the issue
3. Fix the problem
4. Re-run migration

### Important Notes

- **Migration is idempotent**: Safe to run multiple times
- **Only affects AWS**: Other providers are not modified
- **Preserves other fields**: Only `access_key_id` is modified
- **Atomic operation**: Each record is updated in a transaction

### Troubleshooting

#### "ModuleNotFoundError: No module named 'sqlalchemy'"

```bash
# Rebuild backend image with dependencies
docker compose build backend
```

#### "No AWS credentials found in database"

This is normal if:
- Development database has no data yet
- Production database hasn't been configured yet
- Credentials are stored in environment variables only

#### "Failed to decrypt access_key_id"

Possible causes:
- Value is not actually encrypted (false positive)
- Encryption key has changed
- Database corruption

Investigation steps:
1. Check the actual value in database
2. Verify ENCRYPTION_KEY environment variable
3. Check if value starts with "gAAAAA"

### Contact

For issues or questions about this migration:
- Issue: #28
- Stream: Database Migration (Stream C)
- Agent: python-backend-engineer
