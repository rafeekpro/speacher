"""
API Authentication Tests for Speacher Application

Tests follow TDD principles:
- RED phase: Tests will FAIL initially (authentication not fully implemented)
- GREEN phase: Implement authentication to make tests pass
- REFACTOR phase: Improve code while tests stay green

Testing Coverage:
1. Registration Flow
2. Login Flow
3. Protected Endpoint Access
4. User Isolation
5. API Key Authentication
6. Refresh Token Flow

Requirements:
- Real PostgreSQL database (no mocks)
- FastAPI TestClient for testing
- Verbose assertions for debugging
"""

import os
import tempfile
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

# Set test environment variables
os.environ["TESTING"] = "true"
os.environ["DATABASE_URL"] = os.getenv("DATABASE_URL", "postgresql://speacher_user:SpeacherPro4_2024!@10.0.0.5:30432/speacher_test")

# Import application and dependencies
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.main import app
from backend.auth import (
    users_db,
    api_keys_db,
    refresh_tokens_db,
    create_user,
    create_api_key,
    get_user_by_email,
)

# Create test client
client = TestClient(app)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(autouse=True)
def reset_databases():
    """Reset all in-memory databases before each test."""
    users_db.clear()
    api_keys_db.clear()
    refresh_tokens_db.clear()
    yield
    # Cleanup after test
    users_db.clear()
    api_keys_db.clear()
    refresh_tokens_db.clear()


@pytest.fixture
def test_user():
    """Create a test user in the database."""
    user = create_user(
        email="test@example.com",
        password="SecurePass123!",
        full_name="Test User"
    )
    return user


@pytest.fixture
def auth_headers(test_user):
    """Get authentication headers for a test user."""
    from backend.auth import create_access_token

    token = create_access_token({"sub": test_user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def second_user():
    """Create a second test user for isolation tests."""
    user = create_user(
        email="second@example.com",
        password="SecurePass456!",
        full_name="Second User"
    )
    return user


@pytest.fixture
def second_user_headers(second_user):
    """Get authentication headers for second user."""
    from backend.auth import create_access_token

    token = create_access_token({"sub": second_user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_transcription(test_user):
    """Create a test transcription for the first user."""
    from backend.transcriptions_db import transcription_manager

    # Create a transcription for test_user
    doc_id = transcription_manager.save_transcription(
        filename="test_audio.wav",
        provider="aws",
        language="en-US",
        transcript="This is a test transcription.",
        speakers=[],
        enable_diarization=False,
        max_speakers=2,
        duration=10.5,
        cost_estimate=0.05,
        file_size=1024,
        confidence_score=0.95,
        word_count=6,
        user_id=test_user.id,
    )
    return doc_id


@pytest.fixture
def second_user_transcription(second_user):
    """Create a test transcription for the second user."""
    from backend.transcriptions_db import transcription_manager

    doc_id = transcription_manager.save_transcription(
        filename="second_user_audio.wav",
        provider="aws",
        language="en-US",
        transcript="This belongs to second user.",
        speakers=[],
        enable_diarization=False,
        max_speakers=2,
        duration=5.0,
        cost_estimate=0.02,
        file_size=512,
        confidence_score=0.90,
        word_count=5,
        user_id=second_user.id,
    )
    return doc_id


# =============================================================================
# 1. REGISTRATION FLOW TESTS
# =============================================================================

class TestRegistrationFlow:
    """Test user registration endpoint."""

    def test_register_new_user(self, reset_databases):
        """
        Test successful user registration with valid data.

        Expected:
        - HTTP 201 Created status
        - User object returned with id, email, full_name, role
        - Password is not returned in response
        - User exists in database
        """
        response = client.post(
            "/api/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "SecurePass123!",
                "full_name": "New User"
            }
        )

        # Assert response status
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"

        # Assert response data
        data = response.json()
        assert "id" in data, "Response should include user ID"
        assert data["email"] == "newuser@example.com", "Email should match request"
        assert data["full_name"] == "New User", "Full name should match request"
        assert "password" not in data, "Password should not be in response"
        assert "password_hash" not in data, "Password hash should not be in response"

        # Assert user exists in database
        user = get_user_by_email("newuser@example.com")
        assert user is not None, "User should exist in database"
        assert user.id == data["id"], "User ID should match"
        assert user.email == "newuser@example.com", "Email should match in database"

    def test_register_duplicate_email_fails(self, test_user, reset_databases):
        """
        Test registration with duplicate email fails.

        Expected:
        - HTTP 409 Conflict status
        - Error message about duplicate email
        """
        response = client.post(
            "/api/auth/register",
            json={
                "email": "test@example.com",  # Same as test_user
                "password": "AnotherPass123!",
                "full_name": "Duplicate User"
            }
        )

        # Assert conflict status
        assert response.status_code == 409, f"Expected 409, got {response.status_code}: {response.text}"

        # Assert error message
        data = response.json()
        assert "detail" in data, "Response should include error detail"
        assert "already exists" in data["detail"].lower() or "conflict" in data["detail"].lower(), \
            "Error should mention duplicate email"

    def test_register_weak_password_fails(self, reset_databases):
        """
        Test registration with weak password fails validation.

        Testing password requirements:
        - Less than 8 characters
        - No uppercase letter
        - No lowercase letter
        - No number
        - No special character
        """
        weak_passwords = [
            ("short", "Too short"),
            ("nouppercase123!", "No uppercase"),
            ("NOLOWERCASE123!", "No lowercase"),
            ("NoNumbers!", "No numbers"),
            ("NoSpecial123", "No special character"),
        ]

        for password, reason in weak_passwords:
            response = client.post(
                "/api/auth/register",
                json={
                    "email": f"{reason}@example.com",
                    "password": password,
                    "full_name": f"Test {reason}"
                }
            )

            # Assert validation error
            assert response.status_code == 422, \
                f"Expected 422 for {reason}, got {response.status_code}: {response.text}"

            # Assert error message about password
            data = response.json()
            assert "detail" in data, f"Response should include error detail for {reason}"


# =============================================================================
# 2. LOGIN FLOW TESTS
# =============================================================================

class TestLoginFlow:
    """Test user login endpoint."""

    def test_login_with_valid_credentials(self, test_user, reset_databases):
        """
        Test successful login with correct email and password.

        Expected:
        - HTTP 200 OK status
        - Access token returned
        - Refresh token returned
        - Token type is "bearer"
        - User object included in response
        """
        response = client.post(
            "/api/auth/login",
            json={
                "email": "test@example.com",
                "password": "SecurePass123!"
            }
        )

        # Assert success
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        # Assert tokens
        data = response.json()
        assert "access_token" in data, "Response should include access token"
        assert "refresh_token" in data, "Response should include refresh token"
        assert data["token_type"] == "bearer", "Token type should be bearer"
        assert len(data["access_token"]) > 0, "Access token should not be empty"
        assert len(data["refresh_token"]) > 0, "Refresh token should not be empty"

        # Assert user data
        assert "user" in data, "Response should include user object"
        assert data["user"]["email"] == "test@example.com", "User email should match"
        assert data["user"]["id"] == test_user.id, "User ID should match"

    def test_login_with_invalid_password_fails(self, test_user, reset_databases):
        """
        Test login with incorrect password fails.

        Expected:
        - HTTP 401 Unauthorized status
        - Error message about invalid credentials
        - No tokens returned
        """
        response = client.post(
            "/api/auth/login",
            json={
                "email": "test@example.com",
                "password": "WrongPassword123!"
            }
        )

        # Assert unauthorized
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"

        # Assert error message
        data = response.json()
        assert "detail" in data, "Response should include error detail"
        assert "invalid" in data["detail"].lower() or "incorrect" in data["detail"].lower(), \
            "Error should mention invalid credentials"

        # Assert no tokens
        assert "access_token" not in data, "No access token should be returned"
        assert "refresh_token" not in data, "No refresh token should be returned"

    def test_login_nonexistent_user_fails(self, reset_databases):
        """
        Test login with non-existent user email fails.

        Expected:
        - HTTP 401 Unauthorized status
        - Error message about invalid credentials
        - No tokens returned
        """
        response = client.post(
            "/api/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "SomePassword123!"
            }
        )

        # Assert unauthorized
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"

        # Assert error message
        data = response.json()
        assert "detail" in data, "Response should include error detail"
        assert "invalid" in data["detail"].lower() or "incorrect" in data["detail"].lower(), \
            "Error should mention invalid credentials"

        # Assert no tokens
        assert "access_token" not in data, "No access token should be returned"
        assert "refresh_token" not in data, "No refresh token should be returned"


# =============================================================================
# 3. PROTECTED ENDPOINT TESTS
# =============================================================================

class TestProtectedEndpoints:
    """Test authentication on protected endpoints."""

    def test_transcribe_without_auth_fails(self, reset_databases):
        """
        Test /api/transcribe endpoint requires authentication.

        Expected:
        - HTTP 401 Unauthorized status
        - Error message about missing authentication
        """
        # Create a fake WAV file
        wav_data = b"RIFF\x24\x00\x00\x00WAVEfmt "

        response = client.post(
            "/api/transcribe",
            files={"file": ("test.wav", wav_data, "audio/wav")},
            data={
                "provider": "aws",
                "language": "en-US",
                "enable_diarization": "true",
                "max_speakers": "2"
            }
        )

        # Assert unauthorized
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"

        # Assert error message
        data = response.json()
        assert "detail" in data, "Response should include error detail"
        assert "authentication" in data["detail"].lower() or "auth" in data["detail"].lower(), \
            "Error should mention authentication required"

    def test_transcribe_with_valid_jwt_succeeds(self, auth_headers, reset_databases):
        """
        Test /api/transcribe endpoint works with valid JWT.

        Expected:
        - Request passes authentication
        - Returns 200 OK or transcription result
        - Or at least doesn't fail with 401
        """
        # Create a fake WAV file with proper header
        wav_data = b"RIFF\x24\x00\x00\x00WAVEfmt " + b"\x00" * 100

        response = client.post(
            "/api/transcribe",
            files={"file": ("test.wav", wav_data, "audio/wav")},
            data={
                "provider": "aws",
                "language": "en-US",
                "enable_diarization": "true",
                "max_speakers": "2"
            },
            headers=auth_headers
        )

        # Assert not unauthorized (may fail for other reasons like AWS config)
        assert response.status_code != 401, \
            f"Should not return 401 with valid token: {response.text}"

        # May fail with 400/500 if AWS not configured, but that's OK
        # We're testing auth, not transcription functionality
        if response.status_code in [400, 500]:
            # Expected if AWS not configured
            pass
        else:
            # If it succeeds, check response structure
            assert response.status_code == 200 or response.status_code in [400, 500], \
                f"Unexpected status code: {response.status_code}"

    def test_history_without_auth_fails(self, reset_databases):
        """
        Test /api/history endpoint requires authentication.

        Expected:
        - HTTP 401 Unauthorized status
        """
        response = client.get("/api/history")

        assert response.status_code == 401, \
            f"Expected 401, got {response.status_code}: {response.text}"

    def test_history_with_valid_jwt_succeeds(self, auth_headers, reset_databases):
        """
        Test /api/history endpoint works with valid JWT.

        Expected:
        - HTTP 200 OK status
        - Returns list (possibly empty)
        """
        response = client.get("/api/history", headers=auth_headers)

        assert response.status_code == 200, \
            f"Expected 200, got {response.status_code}: {response.text}"

        # Should return a list
        data = response.json()
        assert isinstance(data, list), "History should return a list"

    def test_transcribe_with_expired_token_fails(self, test_user, reset_databases):
        """
        Test /api/transcribe rejects expired JWT token.

        Expected:
        - HTTP 401 Unauthorized status
        - Error message about expired token
        """
        from backend.auth import create_access_token
        from datetime import timedelta

        # Create an expired token (expired 1 hour ago)
        expired_token = create_access_token(
            {"sub": test_user.email},
            expires_delta=timedelta(hours=-1)
        )

        headers = {"Authorization": f"Bearer {expired_token}"}

        wav_data = b"RIFF\x24\x00\x00\x00WAVEfmt " + b"\x00" * 100
        response = client.post(
            "/api/transcribe",
            files={"file": ("test.wav", wav_data, "audio/wav")},
            data={"provider": "aws", "language": "en-US"},
            headers=headers
        )

        # Assert unauthorized
        assert response.status_code == 401, \
            f"Expected 401 for expired token, got {response.status_code}: {response.text}"

        # Assert error message
        data = response.json()
        assert "detail" in data, "Response should include error detail"
        assert "expired" in data["detail"].lower() or "invalid" in data["detail"].lower(), \
            "Error should mention expired or invalid token"

    def test_transcribe_with_invalid_token_fails(self, reset_databases):
        """
        Test /api/transcribe rejects malformed JWT token.

        Expected:
        - HTTP 401 Unauthorized status
        - Error message about invalid token
        """
        headers = {"Authorization": "Bearer invalid.jwt.token"}

        wav_data = b"RIFF\x24\x00\x00\x00WAVEfmt " + b"\x00" * 100
        response = client.post(
            "/api/transcribe",
            files={"file": ("test.wav", wav_data, "audio/wav")},
            data={"provider": "aws", "language": "en-US"},
            headers=headers
        )

        # Assert unauthorized
        assert response.status_code == 401, \
            f"Expected 401 for invalid token, got {response.status_code}: {response.text}"

        # Assert error message
        data = response.json()
        assert "detail" in data, "Response should include error detail"
        assert "invalid" in data["detail"].lower() or "token" in data["detail"].lower(), \
            "Error should mention invalid token"


# =============================================================================
# 4. USER ISOLATION TESTS
# =============================================================================

class TestUserIsolation:
    """Test that users can only access their own data."""

    def test_user_cannot_access_other_user_transcription(
        self, auth_headers, second_user_headers, test_transcription, reset_databases
    ):
        """
        Test user cannot access another user's transcription.

        Expected:
        - HTTP 403 Forbidden status
        - Error message about permission denied
        """
        # Try to access test_user's transcription as second_user
        response = client.get(
            f"/api/transcription/{test_transcription}",
            headers=second_user_headers
        )

        # Assert forbidden
        assert response.status_code == 403, \
            f"Expected 403, got {response.status_code}: {response.text}"

        # Assert error message
        data = response.json()
        assert "detail" in data, "Response should include error detail"
        assert "permission" in data["detail"].lower() or "forbidden" in data["detail"].lower() or \
               "do not have permission" in data["detail"].lower(), \
            "Error should mention permission denied"

    def test_history_returns_only_user_transcriptions(
        self, auth_headers, test_transcription, second_user_transcription, reset_databases
    ):
        """
        Test /api/history returns only current user's transcriptions.

        Expected:
        - Only returns transcriptions created by authenticated user
        - Does not return other users' transcriptions
        """
        # Get history for first user
        response = client.get("/api/history", headers=auth_headers)

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        assert isinstance(data, list), "History should be a list"

        # Should contain first user's transcription
        first_user_transcriptions = [t for t in data if t.get("id") == test_transcription]
        assert len(first_user_transcriptions) > 0, \
            "History should include first user's transcription"

        # Should NOT contain second user's transcription
        second_user_transcriptions = [t for t in data if t.get("id") == second_user_transcription]
        assert len(second_user_transcriptions) == 0, \
            "History should NOT include second user's transcription"

    def test_delete_other_user_transcription_fails(
        self, auth_headers, second_user_headers, test_transcription, reset_databases
    ):
        """
        Test user cannot delete another user's transcription.

        Expected:
        - HTTP 403 Forbidden status
        - Error message about permission denied
        - Original transcription remains in database
        """
        # Try to delete test_user's transcription as second_user
        response = client.delete(
            f"/api/transcription/{test_transcription}",
            headers=second_user_headers
        )

        # Assert forbidden
        assert response.status_code == 403, \
            f"Expected 403, got {response.status_code}: {response.text}"

        # Assert error message
        data = response.json()
        assert "detail" in data, "Response should include error detail"
        assert "permission" in data["detail"].lower() or "forbidden" in data["detail"].lower() or \
               "do not have permission" in data["detail"].lower(), \
            "Error should mention permission denied"

        # Verify transcription still exists for original owner
        response = client.get(
            f"/api/transcription/{test_transcription}",
            headers=auth_headers
        )
        assert response.status_code == 200, \
            "Original transcription should still exist for owner"


# =============================================================================
# 5. API KEY AUTHENTICATION TESTS
# =============================================================================

class TestAPIKeyAuthentication:
    """Test API key authentication."""

    def test_create_api_key(self, test_user, reset_databases):
        """
        Test API key creation for a user.

        Expected:
        - API key is generated
        - API key is stored in database
        - API key has proper attributes (name, user_id, etc.)
        """
        api_key, api_key_db = create_api_key(
            user_id=test_user.id,
            name="Test API Key",
            expires_at=None
        )

        # Assert API key generated
        assert api_key is not None, "API key should be generated"
        assert len(api_key) > 0, "API key should not be empty"
        assert isinstance(api_key, str), "API key should be a string"

        # Assert API key database record
        assert api_key_db is not None, "API key database record should be created"
        assert api_key_db.user_id == test_user.id, "API key should belong to user"
        assert api_key_db.name == "Test API Key", "API key name should match"
        assert api_key_db.key_hash is not None, "API key should have a hash"

    def test_authenticate_with_api_key(self, test_user, reset_databases):
        """
        Test authentication using API key.

        Expected:
        - API key in X-API-Key header authenticates user
        - User can access protected endpoints
        """
        # Create API key
        api_key, _ = create_api_key(
            user_id=test_user.id,
            name="Test Key"
        )

        # Use API key to access protected endpoint
        headers = {"X-API-Key": api_key}
        response = client.get("/api/history", headers=headers)

        # Assert success
        assert response.status_code == 200, \
            f"Expected 200 with API key, got {response.status_code}: {response.text}"

        # Assert response is a list
        data = response.json()
        assert isinstance(data, list), "History should return a list"

    def test_api_key_authentication_succeeds(self, test_user, reset_databases):
        """
        Test API key works like JWT for transcribe endpoint.

        Expected:
        - API key header authenticates request
        - Request passes authentication check
        """
        # Create API key
        api_key, _ = create_api_key(
            user_id=test_user.id,
            name="Transcription Key"
        )

        # Use API key for transcribe
        headers = {"X-API-Key": api_key}
        wav_data = b"RIFF\x24\x00\x00\x00WAVEfmt " + b"\x00" * 100

        response = client.post(
            "/api/transcribe",
            files={"file": ("test.wav", wav_data, "audio/wav")},
            data={"provider": "aws", "language": "en-US"},
            headers=headers
        )

        # Assert not unauthorized (may fail for other reasons)
        assert response.status_code != 401, \
            f"Should not return 401 with valid API key: {response.text}"

    def test_expired_api_key_fails(self, test_user, reset_databases):
        """
        Test expired API key is rejected.

        Expected:
        - HTTP 401 Unauthorized status
        - Error message about expired API key
        """
        from datetime import timedelta

        # Create expired API key
        expires_at = datetime.utcnow() - timedelta(hours=1)
        api_key, _ = create_api_key(
            user_id=test_user.id,
            name="Expired Key",
            expires_at=expires_at
        )

        # Try to use expired API key
        headers = {"X-API-Key": api_key}
        response = client.get("/api/history", headers=headers)

        # Assert unauthorized
        assert response.status_code == 401, \
            f"Expected 401 for expired API key, got {response.status_code}: {response.text}"

        # Assert error message
        data = response.json()
        assert "detail" in data, "Response should include error detail"
        assert "expired" in data["detail"].lower(), \
            "Error should mention expired API key"

    def test_invalid_api_key_fails(self, reset_databases):
        """
        Test invalid API key is rejected.

        Expected:
        - HTTP 401 Unauthorized status
        - Error message about invalid credentials
        """
        headers = {"X-API-Key": "invalid_api_key_12345"}
        response = client.get("/api/history", headers=headers)

        # Assert unauthorized
        assert response.status_code == 401, \
            f"Expected 401 for invalid API key, got {response.status_code}: {response.text}"

        # Assert error message
        data = response.json()
        assert "detail" in data, "Response should include error detail"
        assert "authentication" in data["detail"].lower() or "invalid" in data["detail"].lower(), \
            "Error should mention authentication failed or invalid key"


# =============================================================================
# 6. REFRESH TOKEN TESTS
# =============================================================================

class TestRefreshTokenFlow:
    """Test refresh token functionality."""

    def test_login_returns_refresh_token(self, test_user, reset_databases):
        """
        Test login response includes refresh token.

        Expected:
        - Refresh token is in response
        - Refresh token is different from access token
        - Refresh token is valid JWT format
        """
        response = client.post(
            "/api/auth/login",
            json={
                "email": "test@example.com",
                "password": "SecurePass123!"
            }
        )

        # Assert success
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        # Assert refresh token
        data = response.json()
        assert "refresh_token" in data, "Response should include refresh token"
        assert "access_token" in data, "Response should include access token"
        assert data["refresh_token"] != data["access_token"], \
            "Refresh token should be different from access token"
        assert len(data["refresh_token"]) > 0, "Refresh token should not be empty"

    def test_refresh_token_gets_new_access_token(self, test_user, reset_databases):
        """
        Test refresh token can be used to get new access token.

        Expected:
        - POST to /api/auth/refresh with valid refresh token
        - Returns new access token
        - New access token is valid
        """
        # First, login to get refresh token
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "test@example.com",
                "password": "SecurePass123!"
            }
        )

        login_data = login_response.json()
        original_access_token = login_data["access_token"]
        refresh_token = login_data["refresh_token"]

        # Use refresh token to get new access token
        refresh_response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_token}
        )

        # Assert success
        assert refresh_response.status_code == 200, \
            f"Expected 200, got {refresh_response.status_code}: {refresh_response.text}"

        # Assert new access token
        refresh_data = refresh_response.json()
        assert "access_token" in refresh_data, "Response should include new access token"
        assert refresh_data["access_token"] != original_access_token, \
            "New access token should be different from original"
        assert len(refresh_data["access_token"]) > 0, "New access token should not be empty"

        # Verify new token works
        headers = {"Authorization": f"Bearer {refresh_data['access_token']}"}
        response = client.get("/api/history", headers=headers)
        assert response.status_code == 200, "New access token should work"

    def test_expired_refresh_token_fails(self, test_user, reset_databases):
        """
        Test expired refresh token is rejected.

        Expected:
        - HTTP 401 Unauthorized status
        - Error message about expired or invalid token
        """
        from backend.auth import create_refresh_token
        from datetime import timedelta

        # Create expired refresh token
        expired_token = create_refresh_token(
            {"sub": test_user.email},
            expires_delta=timedelta(days=-1)
        )

        # Try to use expired refresh token
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": expired_token}
        )

        # Assert unauthorized
        assert response.status_code == 401, \
            f"Expected 401 for expired refresh token, got {response.status_code}: {response.text}"

        # Assert error message
        data = response.json()
        assert "detail" in data, "Response should include error detail"
        assert "expired" in data["detail"].lower() or "invalid" in data["detail"].lower(), \
            "Error should mention expired or invalid token"

    def test_invalid_refresh_token_fails(self, reset_databases):
        """
        Test invalid refresh token is rejected.

        Expected:
        - HTTP 401 Unauthorized status
        - Error message about invalid token
        """
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": "invalid.refresh.token"}
        )

        # Assert unauthorized
        assert response.status_code == 401, \
            f"Expected 401 for invalid refresh token, got {response.status_code}: {response.text}"

        # Assert error message
        data = response.json()
        assert "detail" in data, "Response should include error detail"
        assert "invalid" in data["detail"].lower() or "token" in data["detail"].lower(), \
            "Error should mention invalid token"

    def test_access_token_cannot_refresh(self, test_user, reset_databases):
        """
        Test access token cannot be used as refresh token.

        Expected:
        - HTTP 401 Unauthorized status
        - Error message about invalid token type
        """
        # Login to get access token
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "test@example.com",
                "password": "SecurePass123!"
            }
        )

        access_token = login_response.json()["access_token"]

        # Try to use access token as refresh token
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": access_token}
        )

        # Assert unauthorized
        assert response.status_code == 401, \
            f"Expected 401 when using access token as refresh, got {response.status_code}: {response.text}"

        # Assert error message
        data = response.json()
        assert "detail" in data, "Response should include error detail"
        assert "invalid" in data["detail"].lower() or "type" in data["detail"].lower(), \
            "Error should mention invalid token type"


# =============================================================================
# TEST EXECUTION SUMMARY
# =============================================================================

"""
Test Summary:
=============

1. Registration Flow Tests (3 tests)
   - test_register_new_user: Valid registration succeeds
   - test_register_duplicate_email_fails: Duplicate email rejected
   - test_register_weak_password_fails: Weak password validation

2. Login Flow Tests (3 tests)
   - test_login_with_valid_credentials: Successful login returns JWT
   - test_login_with_invalid_password_fails: Wrong password rejected
   - test_login_nonexistent_user_fails: Non-existent user rejected

3. Protected Endpoint Tests (6 tests)
   - test_transcribe_without_auth_fails: 401 without auth header
   - test_transcribe_with_valid_jwt_succeeds: Authenticated request succeeds
   - test_history_without_auth_fails: History requires auth
   - test_history_with_valid_jwt_succeeds: Authenticated history works
   - test_transcribe_with_expired_token_fails: Expired token rejected
   - test_transcribe_with_invalid_token_fails: Invalid token rejected

4. User Isolation Tests (3 tests)
   - test_user_cannot_access_other_user_transcription: 403 when accessing other's data
   - test_history_returns_only_user_transcriptions: History filtered by user
   - test_delete_other_user_transcription_fails: 403 when deleting other's data

5. API Key Authentication Tests (5 tests)
   - test_create_api_key: Generate API key for user
   - test_authenticate_with_api_key: Use API key for history
   - test_api_key_authentication_succeeds: API key works for transcribe
   - test_expired_api_key_fails: Expired API key rejected
   - test_invalid_api_key_fails: Invalid API key rejected

6. Refresh Token Tests (5 tests)
   - test_login_returns_refresh_token: Refresh token included
   - test_refresh_token_gets_new_access_token: Refresh token flow
   - test_expired_refresh_token_fails: Expired refresh rejected
   - test_invalid_refresh_token_fails: Invalid refresh rejected
   - test_access_token_cannot_refresh: Access token can't refresh

Total: 25 comprehensive authentication tests

All tests follow TDD RED phase - they will FAIL initially.
Implement authentication features to make tests pass (GREEN phase).
Then refactor while tests stay green (REFACTOR phase).
"""
