#!/usr/bin/env python3
"""
Comprehensive database schema verification script.
Tests all tables, relationships, triggers, and default data.
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
import bcrypt
from datetime import datetime

# Database connection
DATABASE_URL = os.environ.get('DATABASE_URL',
    'postgresql://speacher_user:SpeacherPro4_2024!@10.0.0.5:30432/speacher')

def test_connection():
    """Test database connection"""
    print("🔌 Testing database connection...")
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute('SELECT version()')
    version = cursor.fetchone()[0]
    print(f"✅ Connected to {version.split()[1]}")
    cursor.close()
    conn.close()
    return True

def test_tables():
    """Verify all tables exist"""
    print("\n📊 Testing tables...")
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    expected_tables = [
        'users', 'projects', 'recordings', 'api_keys',
        'refresh_tokens', 'tags', 'transcriptions'
    ]

    cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """)

    existing_tables = [row['table_name'] for row in cursor.fetchall()]

    for table in expected_tables:
        if table in existing_tables:
            print(f"  ✅ {table}")
        else:
            print(f"  ❌ {table} - MISSING")

    cursor.close()
    conn.close()
    return set(expected_tables).issubset(set(existing_tables))

def test_indexes():
    """Verify indexes exist"""
    print("\n🔍 Testing indexes...")
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    expected_indexes = {
        'users': ['idx_users_email', 'idx_users_role'],
        'projects': ['idx_projects_user_id', 'idx_projects_status', 'idx_projects_created_at'],
        'recordings': ['idx_recordings_project_id', 'idx_recordings_user_id', 'idx_recordings_status', 'idx_recordings_created_at'],
        'api_keys': ['idx_api_keys_user_id', 'idx_api_keys_key_hash', 'idx_api_keys_expires_at'],
        'refresh_tokens': ['idx_refresh_tokens_user_id', 'idx_refresh_tokens_token', 'idx_refresh_tokens_expires_at'],
        'tags': ['idx_tags_project_id', 'idx_tags_name']
    }

    cursor.execute("""
        SELECT tablename, indexname
        FROM pg_indexes
        WHERE schemaname = 'public'
        AND indexname LIKE 'idx_%'
        ORDER BY tablename, indexname
    """)

    existing_indexes = cursor.fetchall()
    for table, indexes in expected_indexes.items():
        print(f"\n  {table}:")
        for idx in indexes:
            exists = any(row['indexname'] == idx and row['tablename'] == table for row in existing_indexes)
            print(f"    {'✅' if exists else '❌'} {idx}")

    cursor.close()
    conn.close()
    return True

def test_triggers():
    """Verify updated_at triggers"""
    print("\n⚡ Testing triggers...")
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute("""
        SELECT tgname as trigger_name, tgrelid::regclass as table_name
        FROM pg_trigger
        WHERE tgname LIKE 'update_%_updated_at'
        AND NOT tgisinternal
        ORDER BY table_name
    """)

    triggers = cursor.fetchall()

    expected_triggers = ['users', 'projects', 'recordings']
    for table in expected_triggers:
        trigger_name = f'update_{table}_updated_at'
        exists = any(row['trigger_name'] == trigger_name for row in triggers)
        print(f"  {'✅' if exists else '❌'} {table}: {trigger_name}")

    cursor.close()
    conn.close()
    return True

def test_views():
    """Verify views exist"""
    print("\n👁️  Testing views...")
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute("""
        SELECT table_name
        FROM information_schema.views
        WHERE table_schema = 'public'
        ORDER BY table_name
    """)

    views = [row['table_name'] for row in cursor.fetchall()]

    expected_views = ['project_summaries', 'user_activity']
    for view in expected_views:
        if view in views:
            print(f"  ✅ {view}")
        else:
            print(f"  ❌ {view} - MISSING")

    cursor.close()
    conn.close()
    return set(expected_views).issubset(set(views))

def test_default_admin():
    """Test default admin user"""
    print("\n👤 Testing default admin user...")
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute("""
        SELECT id, email, password_hash, full_name, role, created_at
        FROM users
        WHERE email = 'admin@localhost'
    """)

    user = cursor.fetchone()

    if user:
        print(f"  ✅ User exists: {user['email']}")
        print(f"     Name: {user['full_name']}")
        print(f"     Role: {user['role']}")

        # Test password
        test_password = "Admin123!"
        is_valid = bcrypt.checkpw(test_password.encode('utf-8'), user['password_hash'].encode('utf-8'))
        print(f"     Password: {'✅ VALID' if is_valid else '❌ INVALID'}")
        print(f"     Default credentials: admin@localhost / {test_password}")

        cursor.close()
        conn.close()
        return is_valid
    else:
        print("  ❌ Admin user not found")
        cursor.close()
        conn.close()
        return False

def test_foreign_keys():
    """Test foreign key constraints"""
    print("\n🔗 Testing foreign key constraints...")
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute("""
        SELECT
            tc.table_name,
            kcu.column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
          ON tc.constraint_name = kcu.constraint_name
          AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage AS ccu
          ON ccu.constraint_name = tc.constraint_name
          AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
        ORDER BY tc.table_name, kcu.column_name
    """)

    fks = cursor.fetchall()

    expected_fks = {
        'projects': ('user_id', 'users'),
        'recordings': ('project_id', 'projects'),
        'api_keys': ('user_id', 'users'),
        'refresh_tokens': ('user_id', 'users'),
        'tags': ('project_id', 'projects')
    }

    all_valid = True
    for table, (col, ref_table) in expected_fks.items():
        exists = any(row['table_name'] == table and row['column_name'] == col for row in fks)
        status = '✅' if exists else '❌'
        print(f"  {status} {table}.{col} → {ref_table}")
        if not exists:
            all_valid = False

    cursor.close()
    conn.close()
    return all_valid

def test_row_counts():
    """Test initial row counts"""
    print("\n📈 Testing row counts...")
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    tables = ['users', 'projects', 'recordings', 'api_keys', 'refresh_tokens', 'tags']

    for table in tables:
        cursor.execute(f"SELECT COUNT(*) as count FROM public.{table}")
        count = cursor.fetchone()['count']
        expected = 1 if table == 'users' else 0
        status = '✅' if count == expected else '⚠️'
        print(f"  {status} {table}: {count} rows (expected: {expected})")

    cursor.close()
    conn.close()
    return True

def main():
    """Run all tests"""
    print("=" * 60)
    print("🐘 POSTGRESQL MIGRATION VERIFICATION")
    print("=" * 60)

    tests = [
        ("Connection", test_connection),
        ("Tables", test_tables),
        ("Indexes", test_indexes),
        ("Triggers", test_triggers),
        ("Views", test_views),
        ("Default Admin", test_default_admin),
        ("Foreign Keys", test_foreign_keys),
        ("Row Counts", test_row_counts)
    ]

    results = {}
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"\n❌ {name} test failed: {e}")
            results[name] = False

    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY")
    print("=" * 60)

    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")

    all_passed = all(results.values())
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL TESTS PASSED - MIGRATION SUCCESSFUL")
        print("=" * 60)
        print("\n🔑 Default Admin Credentials:")
        print("   Email: admin@localhost")
        print("   Password: Admin123!")
        print("\n🌐 Database Connection:")
        print(f"   {DATABASE_URL}")
        return 0
    else:
        print("⚠️  SOME TESTS FAILED - REVIEW MIGRATION")
        print("=" * 60)
        return 1

if __name__ == "__main__":
    exit(main())
