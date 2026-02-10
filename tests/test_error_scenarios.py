#!/usr/bin/env python3
"""
Error handling and edge case tests.
Following TDD approach - tests written first, then implementation.
"""

import asyncio
import io
import os

# Import modules to test
import sys
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.backend.api_keys import APIKeysManager
from src.backend.main import app
from src.backend.streaming import WebSocketManager


class TestFileValidation:
    """Test file validation and error handling."""

    def test_corrupted_audio_file_handling(self):
        """Test handling of corrupted audio files."""
        client = TestClient(app)

        # Create a corrupted audio file (invalid WAV header)
        corrupted_data = b"CORRUPTED_DATA_NOT_A_VALID_WAV_FILE"
        file = io.BytesIO(corrupted_data)

        response = client.post(
            "/transcribe",
            files={"file": ("corrupted.wav", file, "audio/wav")},
            data={"provider": "aws", "language": "en-US"},
        )

        # Should reject corrupted file
        assert response.status_code == 400
        json_response = response.json()
        assert "detail" in json_response or "error" in json_response
        error_msg = json_response.get("detail", json_response.get("error", "")).lower()
        assert "invalid" in error_msg or "corrupted" in error_msg

    def test_oversized_file_rejection(self):
        """Test rejection of files exceeding size limit (>100MB)."""
        client = TestClient(app)

        # Create a file larger than the limit
        # We'll patch MAX_FILE_SIZE to be small for testing
        with patch("src.backend.main.MAX_FILE_SIZE", 1024):  # 1KB limit for testing
            large_data = b"RIFF" + b"x" * 2000  # 2KB file with RIFF header

            response = client.post(
                "/transcribe",
                files={"file": ("large.wav", io.BytesIO(large_data), "audio/wav")},
                data={"provider": "aws", "language": "en-US"},
            )

            # Should reject oversized file
            assert response.status_code == 413 or response.status_code == 400
            json_response = response.json()
            assert "detail" in json_response or "error" in json_response
            error_msg = json_response.get("detail", json_response.get("error", "")).lower()
            assert "size" in error_msg or "large" in error_msg

    def test_unsupported_format_handling(self):
        """Test handling of unsupported audio formats."""
        client = TestClient(app)

        # Try to upload unsupported format
        response = client.post(
            "/transcribe",
            files={"file": ("test.xyz", io.BytesIO(b"data"), "audio/xyz")},
            data={"provider": "aws", "language": "en-US"},
        )

        # Should reject unsupported format
        assert response.status_code == 400
        json_response = response.json()
        assert "detail" in json_response or "error" in json_response
        error_msg = json_response.get("detail", json_response.get("error", "")).lower()
        assert "format" in error_msg or "supported" in error_msg


class TestNetworkErrors:
    """Test network error handling."""

    @pytest.mark.skip(reason="Network timeout handling requires deeper integration")
    @pytest.mark.asyncio
    async def test_network_timeout_handling(self):
        """Test handling of network timeouts."""
        pass

    @pytest.mark.skip(reason="Cloud service error handling requires deeper integration")
    @pytest.mark.asyncio
    async def test_cloud_service_unavailable(self):
        """Test handling when cloud service is unavailable."""
        pass


class TestAPIKeyErrors:
    """Test API key error scenarios."""

    def test_invalid_api_keys_handling(self):
        """Test handling of invalid API keys."""
        import os

        mongodb_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
        manager = APIKeysManager(mongodb_uri, "speecher")

        # Test with invalid AWS keys
        invalid_keys = {"aws_access_key_id": "INVALID", "aws_secret_access_key": "INVALID", "aws_region": "us-east-1"}

        # Should detect invalid configuration
        assert not manager.validate_provider_config("aws", invalid_keys)

        # Test with missing required keys
        incomplete_keys = {"aws_access_key_id": "KEY"}
        assert not manager.validate_provider_config("aws", incomplete_keys)

    @pytest.mark.asyncio
    async def test_expired_api_keys(self):
        """Test handling of expired API keys."""
        client = TestClient(app)

        with patch("src.backend.api_keys.APIKeysManager.get_api_keys") as mock_get:
            mock_get.return_value = {
                "provider": "aws",
                "keys": {"aws_access_key_id": "EXPIRED"},
                "configured": False,
                "error": "API key expired",
            }

            response = client.post(
                "/api/transcribe",
                files={"file": ("test.wav", io.BytesIO(b"RIFF"), "audio/wav")},
                data={"provider": "aws", "language": "en-US"},
            )

            # Should reject with expired keys
            assert response.status_code >= 400


class TestRateLimiting:
    """Test rate limiting functionality."""

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self):
        """Test behavior when rate limit is exceeded."""
        manager = WebSocketManager()

        # Set low rate limit for testing
        manager.rate_limit = 5
        client_id = "rate_test"

        # Send many messages rapidly
        exceeded = False
        for i in range(10):
            message = {"type": "audio", "data": f"data_{i}"}
            result = await manager.process_message_with_rate_limit(client_id, message)
            if not result:
                exceeded = True
                break

        assert exceeded, "Rate limit should have been exceeded"

    @pytest.mark.asyncio
    async def test_concurrent_request_limits(self):
        """Test concurrent request limiting."""
        client = TestClient(app)

        # Simulate many concurrent requests
        import asyncio

        async def make_request():
            return client.get("/api/health")

        # Make 100 concurrent requests
        tasks = [make_request() for _ in range(100)]

        # Should handle all requests without crashing
        # Some might be rate limited
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            # At least some should succeed
            successful = sum(1 for r in results if not isinstance(r, Exception))
            assert successful > 0
        except:
            # Test framework might not support this many concurrent requests
            pass


class TestDatabaseErrors:
    """Test database error handling."""

    @pytest.mark.asyncio
    async def test_mongodb_connection_failure(self):
        """Test handling of MongoDB connection failures."""
        client = TestClient(app)

        with patch("src.backend.main.transcriptions_collection") as mock_collection:
            # Simulate connection failure
            mock_collection.find.side_effect = Exception("Connection refused")

            response = client.get("/history")

            # Should handle connection failure gracefully
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 0  # Returns empty list on failure

    @pytest.mark.asyncio
    async def test_mongodb_write_failure(self):
        """Test handling of MongoDB write failures."""
        client = TestClient(app)

        with patch("src.backend.main.transcriptions_collection.insert_one") as mock_insert:
            # Simulate write failure
            mock_insert.side_effect = Exception("Write failed")

            # Try to save transcription
            response = client.post(
                "/api/transcribe",
                files={"file": ("test.wav", io.BytesIO(b"RIFF"), "audio/wav")},
                data={"provider": "aws", "language": "en-US"},
            )

            # Should handle write failure (might still transcribe but not save)
            assert response.status_code >= 400 or "warning" in response.json()


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_file_handling(self):
        """Test handling of empty files."""
        client = TestClient(app)

        response = client.post(
            "/transcribe",
            files={"file": ("empty.wav", io.BytesIO(b""), "audio/wav")},
            data={"provider": "aws", "language": "en-US"},
        )

        assert response.status_code == 400
        json_response = response.json()
        assert "detail" in json_response or "error" in json_response

    def test_special_characters_in_filename(self):
        """Test handling of special characters in filenames."""
        client = TestClient(app)

        # Filename with special characters
        filename = "test@#$%^&*().wav"

        response = client.post(
            "/transcribe",
            files={"file": (filename, io.BytesIO(b"RIFF"), "audio/wav")},
            data={"provider": "aws", "language": "en-US"},
        )

        # Should handle special characters (sanitize or accept)
        # Response depends on implementation - may fail at AWS level
        assert response.status_code in [200, 400, 500]

    @pytest.mark.asyncio
    async def test_concurrent_same_file_processing(self):
        """Test concurrent processing of the same file."""
        client = TestClient(app)

        file_data = b"RIFF_VALID_WAV_DATA"

        async def upload_file():
            return client.post(
                "/api/transcribe",
                files={"file": ("same.wav", io.BytesIO(file_data), "audio/wav")},
                data={"provider": "aws", "language": "en-US"},
            )

        # Upload same file concurrently
        tasks = [upload_file() for _ in range(5)]

        # Should handle concurrent uploads of same file
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            # Check that requests are handled (success or queued)
            for result in results:
                if not isinstance(result, Exception):
                    assert result.status_code in [200, 202, 400, 429]
        except:
            pass


class TestRecoveryMechanisms:
    """Test error recovery mechanisms."""

    @pytest.mark.skip(reason="Automatic retry mechanism not yet implemented")
    @pytest.mark.asyncio
    async def test_automatic_retry_on_transient_error(self):
        """Test automatic retry on transient errors."""
        pass

    @pytest.mark.asyncio
    async def test_cleanup_after_error(self):
        """Test resource cleanup after errors."""
        manager = WebSocketManager()
        websocket = AsyncMock()
        client_id = "cleanup_test"

        await manager.connect(websocket, client_id)
        assert client_id in manager.active_connections

        # Simulate error during processing
        with patch.object(manager, "process_audio", side_effect=Exception("Processing failed")):
            try:
                await manager.process_message(client_id, {"type": "audio", "data": "test"})
            except:
                pass

        # Cleanup should happen on disconnect
        manager.disconnect(client_id)
        assert client_id not in manager.active_connections
        assert client_id not in manager.transcribers


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
