#!/bin/bash
# Docker-based migration runner for PostgreSQL
# Usage: ./run_migration_docker.sh [migration_file]

set -e

# Database configuration
DB_HOST="${DB_HOST:-10.0.0.5}"
DB_PORT="${DB_PORT:-30432}"
DB_NAME="${DB_NAME:-speacher}"
DB_USER="${DB_USER:-speacher_user}"
DB_PASSWORD="${DB_PASSWORD:-speaker}"

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

# Get absolute path of migration file
MIGRATION_ABS_PATH="$(cd "$(dirname "$MIGRATION_FILE")" && pwd)/$(basename "$MIGRATION_FILE")"

# Run migration using Docker
echo "Running migration: $MIGRATION_FILE"
echo "Database: $DB_USER@$DB_HOST:$DB_PORT/$DB_NAME"
echo ""

docker run -it --rm \
    -v "$(dirname "$MIGRATION_ABS_PATH"):/migrations" \
    postgres:15 \
    psql "postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME" \
    -f "/migrations/$(basename "$MIGRATION_ABS_PATH")"

if [ $? -eq 0 ]; then
    echo ""
    echo "Migration completed successfully!"
else
    echo ""
    echo "Migration failed!"
    exit 1
fi
