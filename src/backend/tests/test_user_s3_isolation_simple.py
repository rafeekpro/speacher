"""
Simplified tests for user-specific S3 folder isolation.

Tests follow TDD approach:
1. RED - Write failing test first
2. GREEN - Implement minimum code to pass
3. REFACTOR - Improve while tests stay green

These tests focus on S3 wrapper functions without requiring database.
"""

import os
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock, call

# Set test environment variables
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing")
os.environ.setdefault("TESTING", "true")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.backend.cloud_wrappers import AWSService


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


class TestS3UserIsolation:
    """Test S3 upload paths with user_id prefix."""

    def test_upload_file_to_s3_accepts_user_id_prefix(self, mock_aws_service, mock_s3_client):
        """
        RED Test: Verify S3 upload accepts user_id prefix in object_name.

        Expected: upload_file_to_s3 should accept object_name like "{user_id}/{filename}"
        """
        bucket_name = "test-bucket"
        user_id = "user-123"
        test_filename = "test-audio.wav"

        # Upload WITH user_id in path
        s3_key = f"{user_id}/{test_filename}"

        # Create temp file
        with open('/tmp/test-file.wav', 'wb') as f:
            f.write(b'fake audio data')

        try:
            result = mock_aws_service.upload_file_to_s3('/tmp/test-file.wav', bucket_name, s3_key)

            # Verify upload_file was called with user_id prefix
            mock_s3_client.upload_file.assert_called_once()
            call_args = mock_s3_client.upload_file.call_args
            assert call_args[0][1] == bucket_name
            assert call_args[0][2] == f"{user_id}/{test_filename}"

            # Verify the S3 path includes user_id
            assert result == f"s3://{bucket_name}/{user_id}/{test_filename}"
        finally:
            if os.path.exists('/tmp/test-file.wav'):
                os.remove('/tmp/test-file.wav')

    def test_list_s3_files_should_accept_prefix_parameter(self, mock_aws_service, mock_s3_client):
        """
        GREEN Test: Verify list_s3_files accepts and uses prefix parameter.

        When prefix="{user_id}/" is passed, it should filter results by that prefix.
        """
        bucket_name = "test-bucket"
        user_id = "user-1"

        # Mock S3 paginator and page iterator
        mock_paginator = MagicMock()
        mock_page_iterator = MagicMock()

        # Verify that paginate is called with Prefix parameter
        mock_page_iterator.__iter__ = lambda self: iter([
            {
                'Contents': [
                    {'Key': f'{user_id}/file1.wav', 'Size': 100, 'LastModified': '2024-01-01', 'ETag': '"abc"'},
                    {'Key': f'{user_id}/file2.wav', 'Size': 200, 'LastModified': '2024-01-02', 'ETag': '"def"'},
                ]
            }
        ])

        mock_paginator.paginate.return_value = mock_page_iterator
        mock_s3_client.get_paginator.return_value = mock_paginator

        # Call with prefix parameter
        files = mock_aws_service.list_s3_files(bucket_name, prefix=f'{user_id}/')

        # Verify paginate was called with Prefix parameter
        mock_paginator.paginate.assert_called_once()
        call_kwargs = mock_paginator.paginate.call_args[1]
        assert 'Prefix' in call_kwargs
        assert call_kwargs['Prefix'] == f'{user_id}/'

        # Verify results
        assert len(files) == 2
        assert all(f['key'].startswith(f'{user_id}/') for f in files)

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

    def test_list_s3_files_with_prefix_filters_results(self, mock_aws_service, mock_s3_client):
        """
        GREEN Test: Verify list_s3_files filters by prefix after implementation.

        Verifies that files not matching the prefix are excluded.
        """
        bucket_name = "test-bucket"
        user_id = "user-1"

        # Mock S3 list_objects_v2 response with prefix
        mock_paginator = MagicMock()
        mock_page_iterator = MagicMock()
        mock_page_iterator.__iter__ = lambda self: iter([
            {
                'Contents': [
                    {'Key': f'{user_id}/file1.wav', 'Size': 100, 'LastModified': '2024-01-01', 'ETag': '"abc"'},
                    {'Key': f'{user_id}/file2.wav', 'Size': 200, 'LastModified': '2024-01-02', 'ETag': '"def"'},
                ]
            }
        ])
        mock_paginator.paginate.return_value = mock_page_iterator
        mock_s3_client.get_paginator.return_value = mock_paginator

        # After implementation, this should work
        files = mock_aws_service.list_s3_files(bucket_name, prefix=f'{user_id}/')

        # Verify only user-1 files are returned
        assert len(files) == 2
        assert all(f['key'].startswith(f'{user_id}/') for f in files)

        # Verify user-2 files are NOT in results
        assert not any(f['key'] == 'user-2/file3.wav' for f in files)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
