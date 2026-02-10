"""
Comprehensive database tests for users_db and projects_db.

Tests follow TDD principles - they will FAIL initially (RED phase).
All tests use real PostgreSQL - no mocks.
"""

import pytest
from datetime import datetime, timedelta
from typing import AsyncGenerator
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import (
    get_db,
    UserDB,
    ProjectDB,
    UserCreate,
    ProjectCreate,
    RecordingCreate,
    TagCreate
)


# =============================================================================
# Test Configuration
# =============================================================================

TEST_DATABASE_URL = "postgresql://postgres:postgres@10.0.0.5:30432/speecher_test"

# Test data constants
TEST_USER_EMAIL = "test@example.com"
TEST_USER_PASSWORD = "SecurePassword123!"
TEST_USER_NAME = "Test User"

TEST_PROJECT_NAME = "Test Project"
TEST_PROJECT_DESCRIPTION = "Test project description"

TEST_RECORDING_NAME = "Test Recording"
TEST_RECORDING_S3_KEY = "test/recording.mp3"
TEST_RECORDING_DURATION = 120.5

TEST_TAG_NAME = "test-tag"
TEST_TAG_COLOR = "#FF0000"


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(scope="session")
async def database():
    """Create database connection for test session."""
    from database import init_db

    # Initialize database with test database
    await init_db(TEST_DATABASE_URL)

    yield

    # Cleanup after all tests
    await close_db()


@pytest.fixture(autouse=True)
async def clean_database(database):
    """Clean database before each test."""
    db = get_db()

    # Clean all tables in correct order (respecting foreign keys)
    async with db.acquire() as conn:
        await conn.execute("""
            DELETE FROM tags;
            DELETE FROM recordings;
            DELETE FROM projects;
            DELETE FROM refresh_tokens;
            DELETE FROM api_keys;
            DELETE FROM users;
        """)

    yield

    # Cleanup after test
    async with db.acquire() as conn:
        await conn.execute("""
            DELETE FROM tags;
            DELETE FROM recordings;
            DELETE FROM projects;
            DELETE FROM refresh_tokens;
            DELETE FROM api_keys;
            DELETE FROM users;
        """)


@pytest.fixture
async def user_db() -> UserDB:
    """Get UserDB instance."""
    return UserDB()


@pytest.fixture
async def project_db() -> ProjectDB:
    """Get ProjectDB instance."""
    return ProjectDB()


@pytest.fixture
async def test_user(user_db: UserDB) -> dict:
    """Create a test user and return user data."""
    user_data = UserCreate(
        email=TEST_USER_EMAIL,
        password=TEST_USER_PASSWORD,
        name=TEST_USER_NAME
    )
    user = await user_db.create_user(user_data)
    return {
        "id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "password": TEST_USER_PASSWORD
    }


@pytest.fixture
async def test_project(project_db: ProjectDB, test_user: dict) -> dict:
    """Create a test project and return project data."""
    project_data = ProjectCreate(
        name=TEST_PROJECT_NAME,
        description=TEST_PROJECT_DESCRIPTION,
        user_id=test_user["id"]
    )
    project = await project_db.create_project(project_data)
    return {
        "id": project["id"],
        "name": project["name"],
        "description": project["description"],
        "user_id": project["user_id"]
    }


# =============================================================================
# Database Connection Tests
# =============================================================================

@pytest.mark.asyncio
async def test_database_connection(database):
    """Test that database connection works."""
    db = get_db()

    # Simple query to test connection
    async with db.acquire() as conn:
        result = await conn.fetchval("SELECT 1 as test")

    assert result == 1, "Database connection failed - could not execute simple query"
    print("✓ Database connection successful")


@pytest.mark.asyncio
async def test_database_tables_exist(database):
    """Test that all required tables exist."""
    db = get_db()

    async with db.acquire() as conn:
        # Check each table exists
        tables = await conn.fetch("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)

    table_names = [row["table_name"] for row in tables]

    required_tables = [
        "users",
        "api_keys",
        "refresh_tokens",
        "projects",
        "recordings",
        "tags"
    ]

    for table in required_tables:
        assert table in table_names, f"Required table '{table}' not found in database"

    print(f"✓ All required tables exist: {', '.join(required_tables)}")


# =============================================================================
# UserDB Tests - User Creation
# =============================================================================

@pytest.mark.asyncio
async def test_create_user(user_db: UserDB):
    """Test creating a new user."""
    user_data = UserCreate(
        email=TEST_USER_EMAIL,
        password=TEST_USER_PASSWORD,
        name=TEST_USER_NAME
    )

    user = await user_db.create_user(user_data)

    # Verify user object structure
    assert user is not None, "User creation returned None"
    assert "id" in user, "User object missing 'id' field"
    assert "email" in user, "User object missing 'email' field"
    assert "name" in user, "User object missing 'name' field"
    assert "created_at" in user, "User object missing 'created_at' field"

    # Verify values
    assert user["email"] == TEST_USER_EMAIL, f"Email mismatch: expected {TEST_USER_EMAIL}, got {user['email']}"
    assert user["name"] == TEST_USER_NAME, f"Name mismatch: expected {TEST_USER_NAME}, got {user['name']}"
    assert isinstance(user["id"], int), f"User ID should be int, got {type(user['id'])}"

    # Verify password was hashed (not stored in plain text)
    assert user.get("password_hash") is None, "Password hash should not be returned in user object"

    print(f"✓ User created successfully with ID: {user['id']}")


@pytest.mark.asyncio
async def test_create_duplicate_user_fails(user_db: UserDB):
    """Test that creating duplicate user (same email) fails."""
    user_data = UserCreate(
        email=TEST_USER_EMAIL,
        password=TEST_USER_PASSWORD,
        name=TEST_USER_NAME
    )

    # Create first user
    await user_db.create_user(user_data)

    # Try to create duplicate user
    with pytest.raises(Exception) as exc_info:
        await user_db.create_user(user_data)

    # Verify error message indicates unique constraint violation
    error_msg = str(exc_info.value).lower()
    assert any(keyword in error_msg for keyword in ["unique", "duplicate", "exists"]), \
        f"Expected unique constraint error, got: {exc_info.value}"

    print(f"✓ Duplicate user creation correctly rejected: {exc_info.value}")


@pytest.mark.asyncio
async def test_get_user_by_email(user_db: UserDB):
    """Test retrieving user by email."""
    # Create user first
    user_data = UserCreate(
        email=TEST_USER_EMAIL,
        password=TEST_USER_PASSWORD,
        name=TEST_USER_NAME
    )
    created_user = await user_db.create_user(user_data)

    # Get user by email
    retrieved_user = await user_db.get_user_by_email(TEST_USER_EMAIL)

    assert retrieved_user is not None, "Failed to retrieve user by email"
    assert retrieved_user["id"] == created_user["id"], \
        f"Retrieved user ID mismatch: expected {created_user['id']}, got {retrieved_user['id']}"
    assert retrieved_user["email"] == TEST_USER_EMAIL, \
        f"Retrieved email mismatch: expected {TEST_USER_EMAIL}, got {retrieved_user['email']}"

    print(f"✓ User retrieved by email successfully")


@pytest.mark.asyncio
async def test_get_user_by_id(user_db: UserDB):
    """Test retrieving user by ID."""
    # Create user first
    user_data = UserCreate(
        email=TEST_USER_EMAIL,
        password=TEST_USER_PASSWORD,
        name=TEST_USER_NAME
    )
    created_user = await user_db.create_user(user_data)

    # Get user by ID
    retrieved_user = await user_db.get_user_by_id(created_user["id"])

    assert retrieved_user is not None, "Failed to retrieve user by ID"
    assert retrieved_user["id"] == created_user["id"], \
        f"Retrieved user ID mismatch: expected {created_user['id']}, got {retrieved_user['id']}"
    assert retrieved_user["email"] == TEST_USER_EMAIL, \
        f"Retrieved email mismatch: expected {TEST_USER_EMAIL}, got {retrieved_user['email']}"

    print(f"✓ User retrieved by ID successfully")


@pytest.mark.asyncio
async def test_get_nonexistent_user_returns_none(user_db: UserDB):
    """Test that getting nonexistent user returns None."""
    user = await user_db.get_user_by_email("nonexistent@example.com")
    assert user is None, "Getting nonexistent user should return None"

    user = await user_db.get_user_by_id(99999)
    assert user is None, "Getting nonexistent user by ID should return None"

    print("✓ Nonexistent user queries return None correctly")


# =============================================================================
# UserDB Tests - Password Verification
# =============================================================================

@pytest.mark.asyncio
async def test_verify_password_correct(user_db: UserDB):
    """Test verifying correct password."""
    user_data = UserCreate(
        email=TEST_USER_EMAIL,
        password=TEST_USER_PASSWORD,
        name=TEST_USER_NAME
    )
    user = await user_db.create_user(user_data)

    # Verify correct password
    is_valid = await user_db.verify_password(TEST_USER_PASSWORD, user["email"])

    assert is_valid is True, f"Password verification failed for correct password"

    print("✓ Correct password verified successfully")


@pytest.mark.asyncio
async def test_verify_password_incorrect(user_db: UserDB):
    """Test that incorrect password is rejected."""
    user_data = UserCreate(
        email=TEST_USER_EMAIL,
        password=TEST_USER_PASSWORD,
        name=TEST_USER_NAME
    )
    user = await user_db.create_user(user_data)

    # Verify incorrect password
    is_valid = await user_db.verify_password("WrongPassword123!", user["email"])

    assert is_valid is False, "Incorrect password should be rejected"

    print("✓ Incorrect password correctly rejected")


@pytest.mark.asyncio
async def test_verify_password_nonexistent_user(user_db: UserDB):
    """Test password verification with nonexistent user."""
    is_valid = await user_db.verify_password(TEST_USER_PASSWORD, "nonexistent@example.com")

    assert is_valid is False, "Password verification for nonexistent user should return False"

    print("✓ Password verification for nonexistent user returns False")


# =============================================================================
# UserDB Tests - User Update
# =============================================================================

@pytest.mark.asyncio
async def test_update_user(user_db: UserDB):
    """Test updating user fields."""
    user_data = UserCreate(
        email=TEST_USER_EMAIL,
        password=TEST_USER_PASSWORD,
        name=TEST_USER_NAME
    )
    user = await user_db.create_user(user_data)

    # Update user
    new_name = "Updated Name"
    updated_user = await user_db.update_user(user["id"], {"name": new_name})

    assert updated_user is not None, "User update returned None"
    assert updated_user["name"] == new_name, \
        f"Name not updated: expected '{new_name}', got '{updated_user['name']}'"
    assert updated_user["email"] == TEST_USER_EMAIL, "Email should not change"

    # Verify update persisted
    retrieved_user = await user_db.get_user_by_id(user["id"])
    assert retrieved_user["name"] == new_name, "Update not persisted in database"

    print(f"✓ User updated successfully: name changed to '{new_name}'")


@pytest.mark.asyncio
async def test_update_user_password(user_db: UserDB):
    """Test updating user password."""
    user_data = UserCreate(
        email=TEST_USER_EMAIL,
        password=TEST_USER_PASSWORD,
        name=TEST_USER_NAME
    )
    user = await user_db.create_user(user_data)

    # Update password
    new_password = "NewSecurePassword456!"
    updated_user = await user_db.update_user(user["id"], {"password": new_password})

    assert updated_user is not None, "Password update returned None"

    # Verify old password doesn't work
    old_valid = await user_db.verify_password(TEST_USER_PASSWORD, user["email"])
    assert old_valid is False, "Old password should no longer work"

    # Verify new password works
    new_valid = await user_db.verify_password(new_password, user["email"])
    assert new_valid is True, "New password should work"

    print("✓ User password updated successfully")


@pytest.mark.asyncio
async def test_update_nonexistent_user(user_db: UserDB):
    """Test updating nonexistent user."""
    result = await user_db.update_user(99999, {"name": "New Name"})

    assert result is None, "Updating nonexistent user should return None"

    print("✓ Updating nonexistent user returns None")


# =============================================================================
# UserDB Tests - User Deletion
# =============================================================================

@pytest.mark.asyncio
async def test_delete_user(user_db: UserDB):
    """Test deleting user."""
    user_data = UserCreate(
        email=TEST_USER_EMAIL,
        password=TEST_USER_PASSWORD,
        name=TEST_USER_NAME
    )
    user = await user_db.create_user(user_data)

    # Delete user
    deleted = await user_db.delete_user(user["id"])

    assert deleted is True, "User deletion should return True"

    # Verify user is gone
    retrieved_user = await user_db.get_user_by_id(user["id"])
    assert retrieved_user is None, "User should be deleted from database"

    print(f"✓ User deleted successfully")


@pytest.mark.asyncio
async def test_delete_nonexistent_user(user_db: UserDB):
    """Test deleting nonexistent user."""
    deleted = await user_db.delete_user(99999)

    assert deleted is False, "Deleting nonexistent user should return False"

    print("✓ Deleting nonexistent user returns False")


# =============================================================================
# UserDB Tests - API Keys
# =============================================================================

@pytest.mark.asyncio
async def test_create_api_key(user_db: UserDB, test_user: dict):
    """Test creating API key for user."""
    api_key = await user_db.create_api_key(
        test_user["id"],
        name="Test API Key",
        expires_days=30
    )

    assert api_key is not None, "API key creation returned None"
    assert "key" in api_key, "API key response missing 'key' field"
    assert "name" in api_key, "API key response missing 'name' field"
    assert "expires_at" in api_key, "API key response missing 'expires_at' field"

    # Verify key format (should be long random string)
    assert len(api_key["key"]) >= 32, f"API key too short: {len(api_key['key'])} chars"

    print(f"✓ API key created: {api_key['key'][:8]}...")


@pytest.mark.asyncio
async def test_verify_api_key(user_db: UserDB, test_user: dict):
    """Test verifying API key."""
    # Create API key
    api_key_data = await user_db.create_api_key(
        test_user["id"],
        name="Test API Key",
        expires_days=30
    )

    # Verify API key
    user = await user_db.verify_api_key(api_key_data["key"])

    assert user is not None, "Valid API key verification failed"
    assert user["id"] == test_user["id"], \
        f"API key returned wrong user: expected {test_user['id']}, got {user['id']}"

    print("✓ API key verified successfully")


@pytest.mark.asyncio
async def test_verify_invalid_api_key(user_db: UserDB):
    """Test that invalid API key is rejected."""
    user = await user_db.verify_api_key("invalid_key_12345")

    assert user is None, "Invalid API key should be rejected"

    print("✓ Invalid API key correctly rejected")


@pytest.mark.asyncio
async def test_api_key_expiration(user_db: UserDB, test_user: dict):
    """Test that expired API keys are rejected."""
    # Create expired API key (expired yesterday)
    api_key_data = await user_db.create_api_key(
        test_user["id"],
        name="Expired Key",
        expires_days=-1
    )

    # Try to verify expired key
    user = await user_db.verify_api_key(api_key_data["key"])

    assert user is None, "Expired API key should be rejected"

    print("✓ Expired API key correctly rejected")


@pytest.mark.asyncio
async def test_list_api_keys(user_db: UserDB, test_user: dict):
    """Test listing user's API keys."""
    # Create multiple API keys
    await user_db.create_api_key(test_user["id"], "Key 1", expires_days=30)
    await user_db.create_api_key(test_user["id"], "Key 2", expires_days=30)

    # List API keys
    api_keys = await user_db.list_api_keys(test_user["id"])

    assert len(api_keys) >= 2, f"Expected at least 2 API keys, got {len(api_keys)}"

    print(f"✓ Listed {len(api_keys)} API keys")


@pytest.mark.asyncio
async def test_delete_api_key(user_db: UserDB, test_user: dict):
    """Test deleting API key."""
    # Create API key
    api_key_data = await user_db.create_api_key(
        test_user["id"],
        name="Key to Delete",
        expires_days=30
    )

    # Delete API key
    deleted = await user_db.delete_api_key(api_key_data["id"])

    assert deleted is True, "API key deletion should return True"

    # Verify key no longer works
    user = await user_db.verify_api_key(api_key_data["key"])
    assert user is None, "Deleted API key should not work"

    print("✓ API key deleted successfully")


# =============================================================================
# UserDB Tests - Refresh Tokens
# =============================================================================

@pytest.mark.asyncio
async def test_create_refresh_token(user_db: UserDB, test_user: dict):
    """Test creating refresh token."""
    token = await user_db.create_refresh_token(
        test_user["id"],
        expires_days=7
    )

    assert token is not None, "Refresh token creation returned None"
    assert "token" in token, "Refresh token response missing 'token' field"
    assert "expires_at" in token, "Refresh token response missing 'expires_at' field"

    # Verify token format
    assert len(token["token"]) >= 32, f"Refresh token too short: {len(token['token'])} chars"

    print(f"✓ Refresh token created: {token['token'][:16]}...")


@pytest.mark.asyncio
async def test_verify_refresh_token(user_db: UserDB, test_user: dict):
    """Test verifying refresh token."""
    # Create refresh token
    token_data = await user_db.create_refresh_token(
        test_user["id"],
        expires_days=7
    )

    # Verify refresh token
    user_id = await user_db.verify_refresh_token(token_data["token"])

    assert user_id is not None, "Valid refresh token verification failed"
    assert user_id == test_user["id"], \
        f"Refresh token returned wrong user: expected {test_user['id']}, got {user_id}"

    print("✓ Refresh token verified successfully")


@pytest.mark.asyncio
async def test_verify_invalid_refresh_token(user_db: UserDB):
    """Test that invalid refresh token is rejected."""
    user_id = await user_db.verify_refresh_token("invalid_token_12345")

    assert user_id is None, "Invalid refresh token should be rejected"

    print("✓ Invalid refresh token correctly rejected")


@pytest.mark.asyncio
async def test_refresh_token_expiration(user_db: UserDB, test_user: dict):
    """Test that expired refresh tokens are rejected."""
    # Create expired token
    token_data = await user_db.create_refresh_token(
        test_user["id"],
        expires_days=-1
    )

    # Try to verify expired token
    user_id = await user_db.verify_refresh_token(token_data["token"])

    assert user_id is None, "Expired refresh token should be rejected"

    print("✓ Expired refresh token correctly rejected")


@pytest.mark.asyncio
async def test_delete_refresh_token(user_db: UserDB, test_user: dict):
    """Test deleting refresh token."""
    # Create refresh token
    token_data = await user_db.create_refresh_token(
        test_user["id"],
        expires_days=7
    )

    # Delete refresh token
    deleted = await user_db.delete_refresh_token(token_data["token"])

    assert deleted is True, "Refresh token deletion should return True"

    # Verify token no longer works
    user_id = await user_db.verify_refresh_token(token_data["token"])
    assert user_id is None, "Deleted refresh token should not work"

    print("✓ Refresh token deleted successfully")


@pytest.mark.asyncio
async def test_delete_all_refresh_tokens(user_db: UserDB, test_user: dict):
    """Test deleting all refresh tokens for user."""
    # Create multiple refresh tokens
    await user_db.create_refresh_token(test_user["id"], expires_days=7)
    await user_db.create_refresh_token(test_user["id"], expires_days=7)
    await user_db.create_refresh_token(test_user["id"], expires_days=7)

    # Delete all tokens
    deleted_count = await user_db.delete_all_refresh_tokens(test_user["id"])

    assert deleted_count >= 3, f"Expected to delete at least 3 tokens, deleted {deleted_count}"

    print(f"✓ Deleted {deleted_count} refresh tokens")


# =============================================================================
# ProjectDB Tests - Project Creation
# =============================================================================

@pytest.mark.asyncio
async def test_create_project(project_db: ProjectDB, test_user: dict):
    """Test creating a project."""
    project_data = ProjectCreate(
        name=TEST_PROJECT_NAME,
        description=TEST_PROJECT_DESCRIPTION,
        user_id=test_user["id"]
    )

    project = await project_db.create_project(project_data)

    # Verify project object structure
    assert project is not None, "Project creation returned None"
    assert "id" in project, "Project object missing 'id' field"
    assert "name" in project, "Project object missing 'name' field"
    assert "description" in project, "Project object missing 'description' field"
    assert "user_id" in project, "Project object missing 'user_id' field"
    assert "created_at" in project, "Project object missing 'created_at' field"

    # Verify values
    assert project["name"] == TEST_PROJECT_NAME, \
        f"Project name mismatch: expected {TEST_PROJECT_NAME}, got {project['name']}"
    assert project["description"] == TEST_PROJECT_DESCRIPTION, \
        f"Project description mismatch: expected {TEST_PROJECT_DESCRIPTION}, got {project['description']}"
    assert project["user_id"] == test_user["id"], \
        f"Project user_id mismatch: expected {test_user['id']}, got {project['user_id']}"

    print(f"✓ Project created successfully with ID: {project['id']}")


@pytest.mark.asyncio
async def test_list_projects_user_isolated(project_db: ProjectDB, user_db: UserDB):
    """Test that users can only see their own projects."""
    # Create two users
    user1_data = UserCreate(email="user1@example.com", password="pass1", name="User 1")
    user1 = await user_db.create_user(user1_data)

    user2_data = UserCreate(email="user2@example.com", password="pass2", name="User 2")
    user2 = await user_db.create_user(user2_data)

    # Create projects for user1
    await project_db.create_project(ProjectCreate(
        name="User1 Project 1",
        description="Project for user 1",
        user_id=user1["id"]
    ))
    await project_db.create_project(ProjectCreate(
        name="User1 Project 2",
        description="Another project for user 1",
        user_id=user1["id"]
    ))

    # Create project for user2
    await project_db.create_project(ProjectCreate(
        name="User2 Project",
        description="Project for user 2",
        user_id=user2["id"]
    ))

    # List projects for user1
    user1_projects = await project_db.list_projects(user1["id"])

    # List projects for user2
    user2_projects = await project_db.list_projects(user2["id"])

    # Verify isolation
    assert len(user1_projects) == 2, f"User1 should have 2 projects, got {len(user1_projects)}"
    assert len(user2_projects) == 1, f"User2 should have 1 project, got {len(user2_projects)}"

    # Verify user2's project not in user1's list
    user1_project_names = [p["name"] for p in user1_projects]
    assert "User2 Project" not in user1_project_names, "User isolation failed: user1 can see user2's project"

    # Verify user1's projects not in user2's list
    user2_project_names = [p["name"] for p in user2_projects]
    assert "User1 Project 1" not in user2_project_names, "User isolation failed: user2 can see user1's project"

    print("✓ User project isolation verified correctly")


@pytest.mark.asyncio
async def test_get_project_by_id(project_db: ProjectDB, test_project: dict):
    """Test retrieving project by ID."""
    # Get project by ID
    project = await project_db.get_project_by_id(test_project["id"])

    assert project is not None, "Failed to retrieve project by ID"
    assert project["id"] == test_project["id"], \
        f"Retrieved project ID mismatch: expected {test_project['id']}, got {project['id']}"
    assert project["name"] == TEST_PROJECT_NAME, \
        f"Retrieved name mismatch: expected {TEST_PROJECT_NAME}, got {project['name']}"

    print("✓ Project retrieved by ID successfully")


@pytest.mark.asyncio
async def test_get_project_forbidden_user(project_db: ProjectDB, user_db: UserDB, test_project: dict):
    """Test that user cannot access another user's project."""
    # Create another user
    other_user_data = UserCreate(email="other@example.com", password="pass", name="Other")
    other_user = await user_db.create_user(other_user_data)

    # Try to get project that belongs to test_user
    project = await project_db.get_project_by_id(test_project["id"], other_user["id"])

    assert project is None, "User should not be able to access another user's project"

    print("✓ Cross-user project access correctly blocked")


# =============================================================================
# ProjectDB Tests - Project Update
# =============================================================================

@pytest.mark.asyncio
async def test_update_project(project_db: ProjectDB, test_project: dict):
    """Test updating project."""
    # Update project
    new_name = "Updated Project Name"
    new_description = "Updated description"

    updated_project = await project_db.update_project(
        test_project["id"],
        {"name": new_name, "description": new_description}
    )

    assert updated_project is not None, "Project update returned None"
    assert updated_project["name"] == new_name, \
        f"Project name not updated: expected '{new_name}', got '{updated_project['name']}'"
    assert updated_project["description"] == new_description, \
        f"Description not updated: expected '{new_description}', got '{updated_project['description']}'"

    # Verify update persisted
    retrieved_project = await project_db.get_project_by_id(test_project["id"])
    assert retrieved_project["name"] == new_name, "Update not persisted in database"

    print(f"✓ Project updated successfully")


@pytest.mark.asyncio
async def test_update_nonexistent_project(project_db: ProjectDB):
    """Test updating nonexistent project."""
    result = await project_db.update_project(99999, {"name": "New Name"})

    assert result is None, "Updating nonexistent project should return None"

    print("✓ Updating nonexistent project returns None")


# =============================================================================
# ProjectDB Tests - Project Deletion
# =============================================================================

@pytest.mark.asyncio
async def test_delete_project(project_db: ProjectDB, test_project: dict):
    """Test deleting project."""
    # Delete project
    deleted = await project_db.delete_project(test_project["id"])

    assert deleted is True, "Project deletion should return True"

    # Verify project is gone
    retrieved_project = await project_db.get_project_by_id(test_project["id"])
    assert retrieved_project is None, "Project should be deleted from database"

    print("✓ Project deleted successfully")


@pytest.mark.asyncio
async def test_delete_nonexistent_project(project_db: ProjectDB):
    """Test deleting nonexistent project."""
    deleted = await project_db.delete_project(99999)

    assert deleted is False, "Deleting nonexistent project should return False"

    print("✓ Deleting nonexistent project returns False")


# =============================================================================
# ProjectDB Tests - Recordings
# =============================================================================

@pytest.mark.asyncio
async def test_create_recording(project_db: ProjectDB, test_project: dict):
    """Test creating a recording."""
    recording_data = RecordingCreate(
        name=TEST_RECORDING_NAME,
        s3_key=TEST_RECORDING_S3_KEY,
        duration=TEST_RECORDING_DURATION,
        project_id=test_project["id"]
    )

    recording = await project_db.create_recording(recording_data)

    # Verify recording object structure
    assert recording is not None, "Recording creation returned None"
    assert "id" in recording, "Recording object missing 'id' field"
    assert "name" in recording, "Recording object missing 'name' field"
    assert "s3_key" in recording, "Recording object missing 's3_key' field"
    assert "duration" in recording, "Recording object missing 'duration' field"
    assert "project_id" in recording, "Recording object missing 'project_id' field"
    assert "created_at" in recording, "Recording object missing 'created_at' field"

    # Verify values
    assert recording["name"] == TEST_RECORDING_NAME, \
        f"Recording name mismatch: expected {TEST_RECORDING_NAME}, got {recording['name']}"
    assert recording["s3_key"] == TEST_RECORDING_S3_KEY, \
        f"s3_key mismatch: expected {TEST_RECORDING_S3_KEY}, got {recording['s3_key']}"
    assert recording["duration"] == TEST_RECORDING_DURATION, \
        f"duration mismatch: expected {TEST_RECORDING_DURATION}, got {recording['duration']}"
    assert recording["project_id"] == test_project["id"], \
        f"project_id mismatch: expected {test_project['id']}, got {recording['project_id']}"

    print(f"✓ Recording created successfully with ID: {recording['id']}")


@pytest.mark.asyncio
async def test_list_recordings_user_isolated(project_db: ProjectDB, user_db: UserDB):
    """Test that users can only see recordings in their own projects."""
    # Create two users with projects
    user1_data = UserCreate(email="user1@example.com", password="pass1", name="User 1")
    user1 = await user_db.create_user(user1_data)

    user2_data = UserCreate(email="user2@example.com", password="pass2", name="User 2")
    user2 = await user_db.create_user(user2_data)

    project1 = await project_db.create_project(ProjectCreate(
        name="User1 Project", description="For user 1", user_id=user1["id"]
    ))

    project2 = await project_db.create_project(ProjectCreate(
        name="User2 Project", description="For user 2", user_id=user2["id"]
    ))

    # Create recordings
    await project_db.create_recording(RecordingCreate(
        name="User1 Recording", s3_key="user1.mp3", duration=100.0, project_id=project1["id"]
    ))

    await project_db.create_recording(RecordingCreate(
        name="User2 Recording", s3_key="user2.mp3", duration=100.0, project_id=project2["id"]
    ))

    # List recordings for user1
    user1_recordings = await project_db.list_recordings(user1["id"])

    # List recordings for user2
    user2_recordings = await project_db.list_recordings(user2["id"])

    # Verify isolation
    assert len(user1_recordings) == 1, f"User1 should have 1 recording, got {len(user1_recordings)}"
    assert len(user2_recordings) == 1, f"User2 should have 1 recording, got {len(user2_recordings)}"

    user1_recording_names = [r["name"] for r in user1_recordings]
    assert "User2 Recording" not in user1_recording_names, "User isolation failed for recordings"

    print("✓ Recording user isolation verified correctly")


@pytest.mark.asyncio
async def test_get_recording_by_id(project_db: ProjectDB, test_project: dict):
    """Test retrieving recording by ID."""
    # Create recording
    recording_data = RecordingCreate(
        name=TEST_RECORDING_NAME,
        s3_key=TEST_RECORDING_S3_KEY,
        duration=TEST_RECORDING_DURATION,
        project_id=test_project["id"]
    )
    recording = await project_db.create_recording(recording_data)

    # Get recording by ID
    retrieved_recording = await project_db.get_recording_by_id(recording["id"])

    assert retrieved_recording is not None, "Failed to retrieve recording by ID"
    assert retrieved_recording["id"] == recording["id"], \
        f"Retrieved recording ID mismatch: expected {recording['id']}, got {retrieved_recording['id']}"
    assert retrieved_recording["name"] == TEST_RECORDING_NAME, \
        f"Retrieved name mismatch: expected {TEST_RECORDING_NAME}, got {retrieved_recording['name']}"

    print("✓ Recording retrieved by ID successfully")


@pytest.mark.asyncio
async def test_update_recording_transcription(project_db: ProjectDB, test_project: dict):
    """Test updating recording transcription."""
    # Create recording
    recording_data = RecordingCreate(
        name=TEST_RECORDING_NAME,
        s3_key=TEST_RECORDING_S3_KEY,
        duration=TEST_RECORDING_DURATION,
        project_id=test_project["id"]
    )
    recording = await project_db.create_recording(recording_data)

    # Update transcription
    transcription_text = "This is the transcribed text from the recording."
    updated_recording = await project_db.update_recording(
        recording["id"],
        {"transcription": transcription_text}
    )

    assert updated_recording is not None, "Recording update returned None"
    assert updated_recording["transcription"] == transcription_text, \
        f"Transcription not updated: expected '{transcription_text}', got '{updated_recording['transcription']}'"

    # Verify update persisted
    retrieved_recording = await project_db.get_recording_by_id(recording["id"])
    assert retrieved_recording["transcription"] == transcription_text, "Transcription not persisted"

    print("✓ Recording transcription updated successfully")


@pytest.mark.asyncio
async def test_delete_recording(project_db: ProjectDB, test_project: dict):
    """Test deleting recording."""
    # Create recording
    recording_data = RecordingCreate(
        name=TEST_RECORDING_NAME,
        s3_key=TEST_RECORDING_S3_KEY,
        duration=TEST_RECORDING_DURATION,
        project_id=test_project["id"]
    )
    recording = await project_db.create_recording(recording_data)

    # Delete recording
    deleted = await project_db.delete_recording(recording["id"])

    assert deleted is True, "Recording deletion should return True"

    # Verify recording is gone
    retrieved_recording = await project_db.get_recording_by_id(recording["id"])
    assert retrieved_recording is None, "Recording should be deleted from database"

    print("✓ Recording deleted successfully")


# =============================================================================
# ProjectDB Tests - Tags
# =============================================================================

@pytest.mark.asyncio
async def test_create_tag(project_db: ProjectDB, test_project: dict):
    """Test creating a tag."""
    tag_data = TagCreate(
        name=TEST_TAG_NAME,
        color=TEST_TAG_COLOR,
        project_id=test_project["id"]
    )

    tag = await project_db.create_tag(tag_data)

    # Verify tag object structure
    assert tag is not None, "Tag creation returned None"
    assert "id" in tag, "Tag object missing 'id' field"
    assert "name" in tag, "Tag object missing 'name' field"
    assert "color" in tag, "Tag object missing 'color' field"
    assert "project_id" in tag, "Tag object missing 'project_id' field"

    # Verify values
    assert tag["name"] == TEST_TAG_NAME, \
        f"Tag name mismatch: expected {TEST_TAG_NAME}, got {tag['name']}"
    assert tag["color"] == TEST_TAG_COLOR, \
        f"Tag color mismatch: expected {TEST_TAG_COLOR}, got {tag['color']}"
    assert tag["project_id"] == test_project["id"], \
        f"Tag project_id mismatch: expected {test_project['id']}, got {tag['project_id']}"

    print(f"✓ Tag created successfully with ID: {tag['id']}")


@pytest.mark.asyncio
async def test_list_tags(project_db: ProjectDB, test_project: dict):
    """Test listing tags for project."""
    # Create multiple tags
    await project_db.create_tag(TagCreate(
        name="tag1", color="#FF0000", project_id=test_project["id"]
    ))
    await project_db.create_tag(TagCreate(
        name="tag2", color="#00FF00", project_id=test_project["id"]
    ))
    await project_db.create_tag(TagCreate(
        name="tag3", color="#0000FF", project_id=test_project["id"]
    ))

    # List tags
    tags = await project_db.list_tags(test_project["id"])

    assert len(tags) == 3, f"Expected 3 tags, got {len(tags)}"

    tag_names = [t["name"] for t in tags]
    assert "tag1" in tag_names, "tag1 not found in tags list"
    assert "tag2" in tag_names, "tag2 not found in tags list"
    assert "tag3" in tag_names, "tag3 not found in tags list"

    print(f"✓ Listed {len(tags)} tags successfully")


@pytest.mark.asyncio
async def test_update_tag(project_db: ProjectDB, test_project: dict):
    """Test updating tag."""
    # Create tag
    tag_data = TagCreate(
        name=TEST_TAG_NAME,
        color=TEST_TAG_COLOR,
        project_id=test_project["id"]
    )
    tag = await project_db.create_tag(tag_data)

    # Update tag
    new_name = "updated-tag"
    new_color = "#00FF00"
    updated_tag = await project_db.update_tag(
        tag["id"],
        {"name": new_name, "color": new_color}
    )

    assert updated_tag is not None, "Tag update returned None"
    assert updated_tag["name"] == new_name, \
        f"Tag name not updated: expected '{new_name}', got '{updated_tag['name']}'"
    assert updated_tag["color"] == new_color, \
        f"Tag color not updated: expected '{new_color}', got '{updated_tag['color']}'"

    print(f"✓ Tag updated successfully")


@pytest.mark.asyncio
async def test_delete_tag(project_db: ProjectDB, test_project: dict):
    """Test deleting tag."""
    # Create tag
    tag_data = TagCreate(
        name=TEST_TAG_NAME,
        color=TEST_TAG_COLOR,
        project_id=test_project["id"]
    )
    tag = await project_db.create_tag(tag_data)

    # Delete tag
    deleted = await project_db.delete_tag(tag["id"])

    assert deleted is True, "Tag deletion should return True"

    # Verify tag is gone
    tags = await project_db.list_tags(test_project["id"])
    assert len(tags) == 0, "Tag should be deleted from database"

    print("✓ Tag deleted successfully")


# =============================================================================
# Integration Tests - Cascade Delete
# =============================================================================

@pytest.mark.asyncio
async def test_user_cascade_delete(user_db: UserDB, project_db: ProjectDB):
    """Test that deleting user cascades to all user's data."""
    # Create user
    user_data = UserCreate(
        email="cascade@example.com",
        password="password123",
        name="Cascade User"
    )
    user = await user_db.create_user(user_data)

    # Create project for user
    project = await project_db.create_project(ProjectCreate(
        name="Cascade Project",
        description="To be deleted",
        user_id=user["id"]
    ))

    # Create recording in project
    recording = await project_db.create_recording(RecordingCreate(
        name="Cascade Recording",
        s3_key="cascade.mp3",
        duration=100.0,
        project_id=project["id"]
    ))

    # Create tags
    await project_db.create_tag(TagCreate(
        name="cascade-tag",
        color="#FF0000",
        project_id=project["id"]
    ))

    # Create API keys
    await user_db.create_api_key(user["id"], "Cascade Key", expires_days=30)

    # Create refresh tokens
    await user_db.create_refresh_token(user["id"], expires_days=7)

    # Delete user (should cascade)
    deleted = await user_db.delete_user(user["id"])
    assert deleted is True, "User deletion failed"

    # Verify all user's data is deleted
    user_projects = await project_db.list_projects(user["id"])
    assert len(user_projects) == 0, "User's projects should be cascade deleted"

    user_recordings = await project_db.list_recordings(user["id"])
    assert len(user_recordings) == 0, "User's recordings should be cascade deleted"

    # Verify user is gone
    retrieved_user = await user_db.get_user_by_id(user["id"])
    assert retrieved_user is None, "User should be deleted"

    print("✓ User cascade delete verified - all user data removed")


@pytest.mark.asyncio
async def test_project_cascade_delete(project_db: ProjectDB, test_user: dict):
    """Test that deleting project cascades to recordings and tags."""
    # Create project
    project = await project_db.create_project(ProjectCreate(
        name="Cascade Project",
        description="For cascade test",
        user_id=test_user["id"]
    ))

    # Create multiple recordings
    recording1 = await project_db.create_recording(RecordingCreate(
        name="Recording 1",
        s3_key="rec1.mp3",
        duration=100.0,
        project_id=project["id"]
    ))
    recording2 = await project_db.create_recording(RecordingCreate(
        name="Recording 2",
        s3_key="rec2.mp3",
        duration=200.0,
        project_id=project["id"]
    ))

    # Create multiple tags
    await project_db.create_tag(TagCreate(
        name="tag1",
        color="#FF0000",
        project_id=project["id"]
    ))
    await project_db.create_tag(TagCreate(
        name="tag2",
        color="#00FF00",
        project_id=project["id"]
    ))

    # Delete project (should cascade)
    deleted = await project_db.delete_project(project["id"])
    assert deleted is True, "Project deletion failed"

    # Verify recordings are deleted
    rec1 = await project_db.get_recording_by_id(recording1["id"])
    assert rec1 is None, "Recording 1 should be cascade deleted"

    rec2 = await project_db.get_recording_by_id(recording2["id"])
    assert rec2 is None, "Recording 2 should be cascade deleted"

    # Verify tags are deleted
    tags = await project_db.list_tags(project["id"])
    assert len(tags) == 0, "Tags should be cascade deleted"

    print("✓ Project cascade delete verified - all project data removed")


# =============================================================================
# Test Runner
# =============================================================================

if __name__ == "__main__":
    import asyncio

    print("=" * 80)
    print("DATABASE TEST SUITE")
    print("=" * 80)
    print()
    print("Running comprehensive tests for users_db and projects_db")
    print("Database:", TEST_DATABASE_URL)
    print()
    print("⚠️  EXPECTED BEHAVIOR: Tests will FAIL initially (RED phase)")
    print("   This is TDD - implement code to make tests pass (GREEN phase)")
    print()
    print("=" * 80)
    print()

    # Run pytest
    pytest.main([__file__, "-v", "-s"])
