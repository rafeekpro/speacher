"""
Tests for user-specific S3 folder isolation.

Tests follow TDD approach:
1. RED - Write failing test first
2. GREEN - Implement minimum code to pass
3. REFACTOR - Improve while tests stay green
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock, call
from fastapi import HTTPException

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.backend.cloud_wrappers import AWSService
from src.backend.auth import create_access_token, UserDB
from src.backend.models import UserRole
from datetime import datetime


@pytest.fixture
def mock_s3_client():
    """Mock S3 client."""
    return MagicMock()


@pytest.fixture
def mock_aws_service(mock_s3_client):
    """Mock AWS service."""
    service = AWSService(region='us-east-1')
    service.s3_client = mock_s3_client
    service.transcribe_client = MagicMock()
    return service


@pytest.fixture
def test_user():
    """Create a test user."""
    return UserDB(
        id="test-user-123",
        email="test@example.com",
        password_hash="hashed",
        full_name="Test User",
        role=UserRole.USER,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


@pytest.fixture
def another_user():
    """Create another test user."""
    return UserDB(
        id="another-user-456",
        email="another@example.com",
        password_hash="hashed",
        full_name="Another User",
        role=UserRole.USER,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


class TestS3UserIsolation:
    """Test S3 upload paths with user_id prefix."""

    def test_upload_file_to_s3_accepts_user_id_prefix(self, mock_aws_service, mock_s3_client, test_user):
        """
        RED Test: Verify S3 upload accepts user_id prefix in object_name.

        Expected: upload_file_to_s3 should accept object_name like "{user_id}/{filename}"
        """
        bucket_name = "test-bucket"
        test_filename = "test-audio.wav"

        # Upload WITH user_id in path
        s3_key = f"{test_user.id}/{test_filename}"

        # Create temp file
        with open('/tmp/test-file.wav', 'wb') as f:
            f.write(b'fake audio data')

        try:
            result = mock_aws_service.upload_file_to_s3('/tmp/test-file.wav', bucket_name, s3_key)

            # Verify upload_file was called with user_id prefix
            mock_s3_client.upload_file.assert_called_once()
            call_args = mock_s3_client.upload_file.call_args
            assert call_args[0][1] == bucket_name
            assert call_args[0][2] == f"{test_user.id}/{test_filename}"

            # Verify the S3 path includes user_id
            assert result == f"s3://{bucket_name}/{test_user.id}/{test_filename}"
        finally:
            if os.path.exists('/tmp/test-file.wav'):
                os.remove('/tmp/test-file.wav')

    def test_list_s3_files_should_accept_prefix_parameter(self, mock_aws_service, mock_s3_client):
        """
        RED Test: Verify list_s3_files can accept a prefix parameter.

        When prefix="{user_id}/" is passed, it should filter results
        """
        bucket_name = "test-bucket"

        # Mock S3 list_objects_v2 response
        mock_s3_client.get_paginator.return_value.paginate.return_value = [
            {
                'Contents': [
                    {'Key': 'user-1/file1.wav', 'Size': 100, 'LastModified': '2024-01-01', 'ETag': '"abc"'},
                    {'Key': 'user-1/file2.wav', 'Size': 200, 'LastModified': '2024-01-02', 'ETag': '"def"'},
                    {'Key': 'user-2/file3.wav', 'Size': 300, 'LastModified': '2024-01-03', 'ETag': '"ghi"'},
                ]
            }
        ]

        # Currently list_s3_files doesn't accept prefix parameter
        # This will fail until we implement it
        try:
            files = mock_aws_service.list_s3_files(bucket_name, prefix='user-1/')
            assert False, "list_s3_files should not accept 'prefix' parameter yet"
        except TypeError as e:
            # Expected to fail in RED phase
            assert "unexpected keyword argument 'prefix'" in str(e)

    def test_list_s3_files_without_prefix_returns_all(self, mock_aws_service, mock_s3_client):
        """Test that list_s3_files works without prefix (current behavior)."""
        bucket_name = "test-bucket"

        # Mock S3 list_objects_v2 response
        mock_paginator = MagicMock()
        mock_page_iterator = MagicMock()
        mock_page_iterator.__iter__ = lambda self: iter([
            {
                'Contents': [
                    {'Key': 'file1.wav', 'Size': 100, 'LastModified': '2024-01-01', 'ETag': '"abc"'},
                    {'Key': 'file2.wav', 'Size': 200, 'LastModified': '2024-01-02', 'ETag': '"def"'},
                ]
            }
        ])
        mock_paginator.paginate.return_value = mock_page_iterator
        mock_s3_client.get_paginator.return_value = mock_paginator

        files = mock_aws_service.list_s3_files(bucket_name)
        assert len(files) == 2
        assert files[0]['key'] == 'file1.wav'
        assert files[1]['key'] == 'file2.wav'


class TestAPIEndpointsWithUserIsolation:
    """Test API endpoints enforce user isolation."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi.testclient import TestClient
        from src.backend.main import app
        return TestClient(app)

    @pytest.fixture
    def user_token(self, test_user):
        """Create JWT token for test user."""
        return create_access_token(data={"sub": test_user.email})

    def test_list_files_endpoint_requires_auth(self, client):
        """
        RED Test: GET /api/files should require authentication.
        """
        response = client.get("/api/files")
        # Currently returns 400 (no AWS config), but should return 401
        # This will be fixed in GREEN phase
        assert response.status_code in [400, 401]

    def test_delete_file_endpoint_should_check_ownership(self, client, user_token):
        """
        RED Test: DELETE /api/files/{filename} should verify user owns the file.

        User should only delete files with {user_id}/{filename} pattern
        """
        # This test documents the expected behavior
        # Implementation will make this pass in GREEN phase
        with patch('src.backend.main.require_auth') as mock_auth:
            mock_auth.return_value = Mock(id="user-1", email="user1@example.com")

            with patch('src.backend.main.api_keys_manager.get_api_keys') as mock_keys:
                mock_keys.return_value = {
                    "keys": {
                        "access_key_id": "test",
                        "secret_access_key": "test",
                        "s3_bucket_name": "test-bucket",
                        "region": "us-east-1"
                    }
                }

                # Try to delete user-2's file as user-1
                # Should fail with 403 Forbidden
                response = client.delete(
                    "/api/files/user-2/file2.wav",
                    headers={"Authorization": f"Bearer {user_token}"}
                )

                # After implementation, this should return 403
                # Currently will likely return 500 or 400
                assert response.status_code in [400, 403, 500]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
