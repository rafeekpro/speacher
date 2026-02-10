"""Tests for authentication API endpoints"""

from datetime import datetime, timedelta

import jwt
from fastapi.testclient import TestClient


def get_error_message(response_json):
    """Helper to extract error message from response"""
    if "detail" in response_json:
        if isinstance(response_json["detail"], dict):
            return response_json["detail"].get("message", response_json["detail"].get("detail", ""))
        return str(response_json["detail"])
    return response_json.get("message", "")


class TestAuthenticationAPI:
    """Test suite for authentication endpoints"""

    def test_user_registration_success(self, client: TestClient):
        """Test successful user registration"""
        request_data = {"email": "test@example.com", "password": "SecurePass123!", "full_name": "Test User"}

        response = client.post("/api/auth/register", json=request_data)

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["full_name"] == "Test User"
        assert "id" in data
        assert "password" not in data
        assert "password_hash" not in data

    def test_user_registration_duplicate_email(self, client: TestClient):
        """Test registration with duplicate email"""
        request_data = {"email": "existing@example.com", "password": "SecurePass123!", "full_name": "Test User"}

        # First registration
        response = client.post("/api/auth/register", json=request_data)
        assert response.status_code == 201

        # Duplicate registration
        response = client.post("/api/auth/register", json=request_data)
        assert response.status_code == 409
        data = response.json()
        assert "already exists" in get_error_message(data).lower()

    def test_user_registration_invalid_email(self, client: TestClient):
        """Test registration with invalid email"""
        request_data = {"email": "invalid-email", "password": "SecurePass123!", "full_name": "Test User"}

        response = client.post("/api/auth/register", json=request_data)
        assert response.status_code == 422

    def test_user_registration_weak_password(self, client: TestClient):
        """Test registration with weak password"""
        request_data = {"email": "test@example.com", "password": "weak", "full_name": "Test User"}

        response = client.post("/api/auth/register", json=request_data)
        assert response.status_code == 422
        data = response.json()
        assert "password" in str(data).lower()

    def test_user_login_success(self, client: TestClient):
        """Test successful user login"""
        # Register user first
        register_data = {"email": "login@example.com", "password": "SecurePass123!", "full_name": "Login User"}
        client.post("/api/auth/register", json=register_data)

        # Login
        login_data = {"email": "login@example.com", "password": "SecurePass123!"}
        response = client.post("/api/auth/login", json=login_data)

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
        assert data["user"]["email"] == "login@example.com"

    def test_user_login_invalid_credentials(self, client: TestClient):
        """Test login with invalid credentials"""
        login_data = {"email": "nonexistent@example.com", "password": "WrongPassword123!"}
        response = client.post("/api/auth/login", json=login_data)

        assert response.status_code == 401
        data = response.json()
        assert "invalid" in get_error_message(data).lower()

    def test_user_login_wrong_password(self, client: TestClient):
        """Test login with wrong password"""
        # Register user first
        register_data = {"email": "wrongpass@example.com", "password": "CorrectPass123!", "full_name": "Test User"}
        client.post("/api/auth/register", json=register_data)

        # Login with wrong password
        login_data = {"email": "wrongpass@example.com", "password": "WrongPass123!"}
        response = client.post("/api/auth/login", json=login_data)

        assert response.status_code == 401

    def test_token_refresh_success(self, client: TestClient):
        """Test successful token refresh"""
        # Login to get tokens
        register_data = {"email": "refresh@example.com", "password": "SecurePass123!", "full_name": "Refresh User"}
        client.post("/api/auth/register", json=register_data)

        login_data = {"email": "refresh@example.com", "password": "SecurePass123!"}
        login_response = client.post("/api/auth/login", json=login_data)
        refresh_token = login_response.json()["refresh_token"]

        # Refresh token
        refresh_data = {"refresh_token": refresh_token}
        response = client.post("/api/auth/refresh", json=refresh_data)

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_token_refresh_invalid_token(self, client: TestClient):
        """Test token refresh with invalid token"""
        refresh_data = {"refresh_token": "invalid.token.here"}
        response = client.post("/api/auth/refresh", json=refresh_data)

        assert response.status_code == 401
        data = response.json()
        assert "invalid" in get_error_message(data).lower()

    def test_user_logout(self, client: TestClient):
        """Test user logout"""
        # Login first
        register_data = {"email": "logout@example.com", "password": "SecurePass123!", "full_name": "Logout User"}
        client.post("/api/auth/register", json=register_data)

        login_data = {"email": "logout@example.com", "password": "SecurePass123!"}
        login_response = client.post("/api/auth/login", json=login_data)
        access_token = login_response.json()["access_token"]

        # Logout
        headers = {"Authorization": f"Bearer {access_token}"}
        response = client.post("/api/auth/logout", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "success" in data.get("message", "").lower()

    def test_protected_route_with_valid_token(self, client: TestClient):
        """Test accessing protected route with valid token"""
        # Login to get token
        register_data = {"email": "protected@example.com", "password": "SecurePass123!", "full_name": "Protected User"}
        client.post("/api/auth/register", json=register_data)

        login_data = {"email": "protected@example.com", "password": "SecurePass123!"}
        login_response = client.post("/api/auth/login", json=login_data)
        access_token = login_response.json()["access_token"]

        # Access protected route
        headers = {"Authorization": f"Bearer {access_token}"}
        response = client.get("/api/users/profile", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "protected@example.com"

    def test_protected_route_without_token(self, client: TestClient):
        """Test accessing protected route without token"""
        response = client.get("/api/users/profile")

        assert response.status_code in [401, 403]  # Can be 403 with HTTPBearer
        data = response.json()
        assert "authentication required" in get_error_message(data).lower()

    def test_protected_route_with_expired_token(self, client: TestClient):
        """Test accessing protected route with expired token"""
        from src.backend.auth import SECRET_KEY

        # Create an expired token
        expired_token = jwt.encode(
            {"sub": "test@example.com", "exp": datetime.utcnow() - timedelta(hours=1)}, SECRET_KEY, algorithm="HS256"
        )

        headers = {"Authorization": f"Bearer {expired_token}"}
        response = client.get("/api/users/profile", headers=headers)

        assert response.status_code == 401
        data = response.json()
        assert "authentication required" in get_error_message(data).lower()

    def test_password_complexity_requirements(self, client: TestClient):
        """Test password complexity requirements"""
        test_cases = [
            ("short", 422, "at least 8 characters"),
            ("nouppercase123!", 422, "uppercase"),
            ("NOLOWERCASE123!", 422, "lowercase"),
            ("NoNumbers!", 422, "number"),
            ("NoSpecialChar123", 422, "special character"),
            ("ValidPass123!", 201, None),
        ]

        for i, (password, expected_status, expected_message) in enumerate(test_cases):
            request_data = {"email": f"test{i}@example.com", "password": password, "full_name": "Test User"}

            response = client.post("/api/auth/register", json=request_data)
            assert response.status_code == expected_status

            if expected_message:
                data = response.json()
                assert expected_message in str(data).lower()

    def test_rate_limiting_on_login(self, client: TestClient):
        """Test rate limiting on login endpoint"""
        login_data = {"email": "ratelimit@example.com", "password": "WrongPass123!"}

        # Make multiple failed login attempts
        for _ in range(5):
            response = client.post("/api/auth/login", json=login_data)
            assert response.status_code in [401, 429]

        # Next attempt should be rate limited
        response = client.post("/api/auth/login", json=login_data)
        assert response.status_code == 429
        data = response.json()
        assert "too many" in get_error_message(data).lower() or "rate limit" in get_error_message(data).lower()

    def test_session_management(self, client: TestClient):
        """Test session management"""
        # Register and login
        register_data = {"email": "session@example.com", "password": "SecurePass123!", "full_name": "Session User"}
        client.post("/api/auth/register", json=register_data)

        login_data = {"email": "session@example.com", "password": "SecurePass123!"}
        login_response = client.post("/api/auth/login", json=login_data)
        access_token = login_response.json()["access_token"]

        # Get active sessions
        headers = {"Authorization": f"Bearer {access_token}"}
        response = client.get("/api/auth/sessions", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert len(data["sessions"]) > 0

        # Revoke a session
        session_id = data["sessions"][0]["id"]
        response = client.delete(f"/api/auth/sessions/{session_id}", headers=headers)
        assert response.status_code == 200
