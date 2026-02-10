"""Tests for user management API endpoints"""

import uuid
from typing import Dict

import pytest
from fastapi.testclient import TestClient


def get_error_message(response_json):
    """Helper to extract error message from response"""
    if "detail" in response_json:
        if isinstance(response_json["detail"], dict):
            return response_json["detail"].get("message", response_json["detail"].get("detail", ""))
        return str(response_json["detail"])
    return response_json.get("message", "")


class TestUserManagementAPI:
    """Test suite for user management endpoints"""

    @pytest.fixture
    def authenticated_client(self, client: TestClient) -> tuple[TestClient, Dict[str, str], str]:
        """Create authenticated client for testing"""
        # Generate unique email for each test
        unique_id = str(uuid.uuid4())[:8]
        email = f"auth_user_{unique_id}@example.com"

        # Register user
        register_data = {"email": email, "password": "SecurePass123!", "full_name": "Auth User"}
        reg_response = client.post("/api/auth/register", json=register_data)
        assert reg_response.status_code == 201, f"Registration failed: {reg_response.json()}"

        # Login
        login_data = {"email": email, "password": "SecurePass123!"}
        login_response = client.post("/api/auth/login", json=login_data)
        assert login_response.status_code == 200, f"Login failed: {login_response.json()}"

        tokens = login_response.json()
        assert "access_token" in tokens, f"No access_token in response: {tokens}"

        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        return client, headers, email

    def test_get_user_profile(self, authenticated_client):
        """Test getting user profile"""
        client, headers, email = authenticated_client
        response = client.get("/api/users/profile", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == email
        assert data["full_name"] == "Auth User"
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data
        assert "password" not in data

    def test_update_user_profile(self, authenticated_client):
        """Test updating user profile"""
        client, headers, email = authenticated_client
        update_data = {"full_name": "Updated Name", "email": "newemail@example.com"}

        response = client.put("/api/users/profile", json=update_data, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Updated Name"
        assert data["email"] == "newemail@example.com"

    def test_update_profile_duplicate_email(self, client: TestClient):
        """Test updating profile with duplicate email"""
        # Generate unique emails for two users
        unique_id1 = str(uuid.uuid4())[:8]
        unique_id2 = str(uuid.uuid4())[:8]
        email1 = f"user1_{unique_id1}@example.com"
        email2 = f"user2_{unique_id2}@example.com"

        # Register two users
        for i, email in enumerate([email1, email2]):
            register_data = {"email": email, "password": "SecurePass123!", "full_name": f"User {i+1}"}
            client.post("/api/auth/register", json=register_data)

        # Login as user2
        login_data = {"email": email2, "password": "SecurePass123!"}
        login_response = client.post("/api/auth/login", json=login_data)
        headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

        # Try to update email to user1's email
        update_data = {"email": email1}
        response = client.put("/api/users/profile", json=update_data, headers=headers)

        assert response.status_code == 409
        data = response.json()
        assert "already in use" in get_error_message(data).lower()

    def test_change_password(self, authenticated_client):
        """Test changing user password"""
        client, headers, email = authenticated_client
        change_data = {"current_password": "SecurePass123!", "new_password": "NewSecurePass456!"}

        response = client.put("/api/users/password", json=change_data, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "success" in data["message"].lower()

        # Test login with new password
        login_data = {"email": email, "password": "NewSecurePass456!"}
        login_response = client.post("/api/auth/login", json=login_data)
        assert login_response.status_code == 200

    def test_change_password_wrong_current(self, authenticated_client):
        """Test changing password with wrong current password"""
        client, headers, email = authenticated_client
        change_data = {"current_password": "WrongPassword123!", "new_password": "NewSecurePass456!"}

        response = client.put("/api/users/password", json=change_data, headers=headers)

        assert response.status_code == 401
        data = response.json()
        assert "incorrect" in data["detail"].lower()

    def test_change_password_weak_new(self, authenticated_client):
        """Test changing to weak password"""
        client, headers, email = authenticated_client
        change_data = {"current_password": "SecurePass123!", "new_password": "weak"}

        response = client.put("/api/users/password", json=change_data, headers=headers)

        assert response.status_code == 422
        data = response.json()
        assert "password" in str(data).lower()

    def test_create_api_key(self, authenticated_client):
        """Test creating API key"""
        client, headers, email = authenticated_client
        key_data = {"name": "Test API Key", "expires_at": "2025-12-31T23:59:59"}

        response = client.post("/api/users/api-keys", json=key_data, headers=headers)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test API Key"
        assert "id" in data
        assert "key" in data  # Key is only shown on creation
        assert len(data["key"]) > 20
        assert "created_at" in data
        assert "expires_at" in data

    def test_list_api_keys(self, authenticated_client):
        """Test listing user's API keys"""
        client, headers, email = authenticated_client

        # Create some API keys
        for i in range(3):
            key_data = {"name": f"API Key {i+1}"}
            client.post("/api/users/api-keys", json=key_data, headers=headers)

        # List keys
        response = client.get("/api/users/api-keys", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "keys" in data
        assert len(data["keys"]) >= 3
        # Keys should not include the actual key value
        for key in data["keys"]:
            assert "key" not in key or key["key"] is None
            assert "name" in key
            assert "id" in key

    def test_delete_api_key(self, authenticated_client):
        """Test deleting API key"""
        client, headers, email = authenticated_client

        # Create API key
        key_data = {"name": "Key to Delete"}
        create_response = client.post("/api/users/api-keys", json=key_data, headers=headers)
        key_id = create_response.json()["id"]

        # Delete key
        response = client.delete(f"/api/users/api-keys/{key_id}", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "success" in data["message"].lower()

        # Verify deletion
        list_response = client.get("/api/users/api-keys", headers=headers)
        keys = list_response.json()["keys"]
        assert not any(k["id"] == key_id for k in keys)

    def test_delete_nonexistent_api_key(self, authenticated_client):
        """Test deleting non-existent API key"""
        client, headers, email = authenticated_client

        response = client.delete("/api/users/api-keys/nonexistent-id", headers=headers)

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_api_key_authentication(self, client: TestClient):
        """Test authenticating with API key"""
        # Generate unique email
        unique_id = str(uuid.uuid4())[:8]
        email = f"apikey_{unique_id}@example.com"

        # Register user and get token
        register_data = {"email": email, "password": "SecurePass123!", "full_name": "API Key User"}
        client.post("/api/auth/register", json=register_data)

        login_data = {"email": email, "password": "SecurePass123!"}
        login_response = client.post("/api/auth/login", json=login_data)
        headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

        # Create API key
        key_data = {"name": "Auth Test Key"}
        create_response = client.post("/api/users/api-keys", json=key_data, headers=headers)
        api_key = create_response.json()["key"]

        # Use API key for authentication
        api_headers = {"X-API-Key": api_key}
        response = client.get("/api/users/profile", headers=api_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == email

    def test_expired_api_key(self, client: TestClient):
        """Test using expired API key"""
        # Generate unique email
        unique_id = str(uuid.uuid4())[:8]
        email = f"expired_{unique_id}@example.com"

        # Register user and get token
        register_data = {"email": email, "password": "SecurePass123!", "full_name": "Expired Key User"}
        client.post("/api/auth/register", json=register_data)

        login_data = {"email": email, "password": "SecurePass123!"}
        login_response = client.post("/api/auth/login", json=login_data)
        headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

        # Create API key with past expiration
        key_data = {"name": "Expired Key", "expires_at": "2020-01-01T00:00:00"}
        create_response = client.post("/api/users/api-keys", json=key_data, headers=headers)
        api_key = create_response.json()["key"]

        # Try to use expired key
        api_headers = {"X-API-Key": api_key}
        response = client.get("/api/users/profile", headers=api_headers)

        assert response.status_code == 401
        data = response.json()
        assert "expired" in data["detail"].lower()

    def test_delete_user_account(self, authenticated_client):
        """Test deleting user account"""
        client, headers, email = authenticated_client

        # Delete account
        response = client.delete("/api/users/account?password=SecurePass123!", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "deleted" in data["message"].lower()

        # Verify account is deleted (cannot authenticate)
        response = client.get("/api/users/profile", headers=headers)
        assert response.status_code == 401

    def test_delete_account_wrong_password(self, authenticated_client):
        """Test deleting account with wrong password"""
        client, headers, email = authenticated_client

        response = client.delete("/api/users/account?password=WrongPassword123!", headers=headers)

        assert response.status_code == 401
        data = response.json()
        assert "incorrect" in data["detail"].lower()

    def test_user_activity_log(self, authenticated_client):
        """Test getting user activity log"""
        client, headers, email = authenticated_client

        # Perform some activities
        client.get("/api/users/profile", headers=headers)
        client.put("/api/users/profile", json={"full_name": "New Name"}, headers=headers)

        # Get activity log
        response = client.get("/api/users/activity", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "activities" in data
        assert len(data["activities"]) > 0

        for activity in data["activities"]:
            assert "timestamp" in activity
            assert "action" in activity
            assert "ip_address" in activity
