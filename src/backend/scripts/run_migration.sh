#!/bin/bash
# Migration runner script for PostgreSQL
# Usage: ./run_migration.sh [migration_file]

set -e

# Database configuration
DB_HOST="${DB_HOST:-10.0.0.5}"
DB_PORT="${DB_PORT:-30432}"
DB_NAME="${DB_NAME:-speacher}"
DB_USER="${DB_USER:-speacher_user}"

# Get migration file argument
MIGRATION_FILE="${1:-}"

if [ -z "$MIGRATION_FILE" ]; then
    echo "Usage: $0 <migration_file>"
    echo "Example: $0 migrations/001_initial_schema.sql"
    exit 1
fi

# Check if file exists
if [ ! -f "$MIGRATION_FILE" ]; then
    echo "Error: Migration file not found: $MIGRATION_FILE"
    exit 1
fi

# Run migration
echo "Running migration: $MIGRATION_FILE"
echo "Database: $DB_USER@$DB_HOST:$DB_PORT/$DB_NAME"
echo ""

psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$MIGRATION_FILE"

if [ $? -eq 0 ]; then
    echo ""
    echo "Migration completed successfully!"
else
    echo ""
    echo "Migration failed!"
    exit 1
fi
