#!/usr/bin/env python3
"""
Migration script to decrypt encrypted AWS access_key_id values in the database.

This script addresses Issue #28 where access_key_id was incorrectly encrypted
due to the word "key" matching the sensitive keyword filter.

The script:
1. Fetches all AWS provider credentials from the database
2. Checks if access_key_id is encrypted (starts with "gAAAAAB")
3. Decrypts the access_key_id if encrypted
4. Saves back the credentials with unencrypted access_key_id

IMPORTANT: Run this AFTER fixing the encryption logic in api_keys.py to remove
"key" from the sensitive keywords list.
"""

import os
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.backend.api_keys import APIKeysManager


def is_encrypted(value: str) -> bool:
    """Check if a value is encrypted with Fernet."""
    if not value or not isinstance(value, str):
        return False
    # Fernet encrypted values start with "gAAAAA"
    return value.startswith("gAAAAA")


def migrate_aws_access_key_id(manager: APIKeysManager, dry_run: bool = True) -> dict:
    """
    Migrate AWS credentials to decrypt encrypted access_key_id values.

    Args:
        manager: APIKeysManager instance
        dry_run: If True, only report what would be changed

    Returns:
        Dictionary with migration results
    """
    result = {
        "aws_credentials_found": 0,
        "encrypted_access_key_ids": 0,
        "migrated": 0,
        "skipped": 0,
        "errors": [],
        "details": []
    }

    try:
        # Get AWS credentials from database
        session = manager.SessionLocal()
        from src.backend.api_keys import APIKey

        aws_records = session.query(APIKey).filter_by(provider="aws").all()
        result["aws_credentials_found"] = len(aws_records)

        if not aws_records:
            print("No AWS credentials found in database.")
            return result

        for record in aws_records:
            if not record.keys or not isinstance(record.keys, dict):
                result["skipped"] += 1
                result["details"].append({
                    "status": "skipped",
                    "reason": "No keys or invalid keys format"
                })
                continue

            keys = record.keys
            access_key_id = keys.get("access_key_id")

            if not access_key_id:
                result["skipped"] += 1
                result["details"].append({
                    "status": "skipped",
                    "reason": "No access_key_id found"
                })
                continue

            # Check if access_key_id is encrypted
            if not is_encrypted(access_key_id):
                result["skipped"] += 1
                result["details"].append({
                    "status": "skipped",
                    "reason": "access_key_id is not encrypted",
                    "access_key_id_preview": access_key_id[:8] + "..." if len(access_key_id) > 8 else access_key_id
                })
                print(f"access_key_id is not encrypted: {access_key_id[:8]}...")
                continue

            result["encrypted_access_key_ids"] += 1

            # Decrypt the access_key_id
            try:
                decrypted_access_key = manager.decrypt_value(access_key_id)

                if dry_run:
                    result["details"].append({
                        "status": "would_migrate",
                        "encrypted_preview": access_key_id[:20] + "...",
                        "decrypted_preview": decrypted_access_key[:8] + "..." if len(decrypted_access_key) > 8 else decrypted_access_key
                    })
                    print(f"[DRY RUN] Would decrypt access_key_id: {access_key_id[:20]}... -> {decrypted_access_key[:8]}...")
                else:
                    # Update the keys with decrypted access_key_id
                    keys["access_key_id"] = decrypted_access_key
                    record.keys = keys
                    record.updated_at = None  # Will be set to current time on save

                    session.commit()
                    result["migrated"] += 1
                    result["details"].append({
                        "status": "migrated",
                        "decrypted_preview": decrypted_access_key[:8] + "..." if len(decrypted_access_key) > 8 else decrypted_access_key
                    })
                    print(f"Successfully migrated access_key_id: {decrypted_access_key[:8]}...")

            except Exception as e:
                error_msg = f"Failed to decrypt access_key_id: {str(e)}"
                result["errors"].append(error_msg)
                result["details"].append({
                    "status": "error",
                    "error": error_msg
                })
                print(f"ERROR: {error_msg}")

        session.close()

    except Exception as e:
        error_msg = f"Migration failed: {str(e)}"
        result["errors"].append(error_msg)
        print(f"ERROR: {error_msg}")

    return result


def main():
    """Main migration function."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Migrate encrypted AWS access_key_id values to plain text"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without making changes"
    )
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL"),
        help="PostgreSQL database URL (default: from DATABASE_URL env var)"
    )

    args = parser.parse_args()

    if not args.database_url:
        print("ERROR: DATABASE_URL environment variable not set and --database-url not provided")
        sys.exit(1)

    print("=" * 70)
    print("AWS access_key_id Migration Script")
    print("=" * 70)
    print(f"Database URL: {args.database_url}")
    print(f"Dry Run: {args.dry_run}")
    print()

    # Initialize API keys manager
    manager = APIKeysManager(args.database_url)

    # Run migration
    result = migrate_aws_access_key_id(manager, dry_run=args.dry_run)

    # Print summary
    print()
    print("=" * 70)
    print("Migration Summary")
    print("=" * 70)
    print(f"AWS credentials found: {result['aws_credentials_found']}")
    print(f"Encrypted access_key_ids: {result['encrypted_access_key_ids']}")
    print(f"Migrated: {result['migrated']}")
    print(f"Skipped: {result['skipped']}")
    print(f"Errors: {len(result['errors'])}")

    if result['errors']:
        print()
        print("Errors:")
        for error in result['errors']:
            print(f"  - {error}")

    if args.dry_run and result['encrypted_access_key_ids'] > 0:
        print()
        print("This was a DRY RUN. To apply changes, run without --dry-run")
        print("After fixing the encryption logic in api_keys.py (remove 'key' from sensitive list)")

    # Exit with error code if there were errors
    if result['errors']:
        sys.exit(1)

    # Exit with warning if encrypted access_key_ids were found but dry run
    if args.dry_run and result['encrypted_access_key_ids'] > 0:
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
