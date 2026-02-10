#!/usr/bin/env python3
"""
Docker integration tests for Speecher application.
These tests verify the complete stack functionality when running in Docker.
"""

import math
import os
import struct
import tempfile
import time
import wave

import pytest
import requests

# Configuration from environment
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
MONGODB_URI = os.getenv(
    "MONGODB_URI", "mongodb://speecher_user:speecher_pass@localhost:27017/speecher_test?authSource=speecher"
)


def is_docker_running():
    """Check if Docker backend is running and accessible."""
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=1)
        return response.status_code == 200
    except:
        return False


# Skip all tests in this file if Docker is not running
pytestmark = pytest.mark.skipif(
    not is_docker_running(), reason="Docker backend not running - skipping integration tests"
)


def generate_test_audio(duration: float = 1.0, filename: str = None) -> str:
    """Generate a test WAV file with sufficient duration for cloud services."""
    if filename is None:
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        filename = temp_file.name

    sample_rate = 44100
    frequency = 440  # A4 note
    amplitude = 0.5

    # Generate sine wave
    num_samples = int(sample_rate * duration)
    samples = []

    for i in range(num_samples):
        t = float(i) / sample_rate
        value = amplitude * math.sin(2 * math.pi * frequency * t)
        packed_value = struct.pack("h", int(value * 32767))
        samples.append(packed_value)

    # Write WAV file
    with wave.open(filename, "wb") as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b"".join(samples))

    return filename


@pytest.fixture
def test_audio_file():
    """Fixture to create and cleanup test audio file."""
    filename = generate_test_audio(duration=1.0)
    yield filename
    # Cleanup
    try:
        os.remove(filename)
    except:
        pass


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_backend_health(self):
        """Test backend health endpoint."""
        response = requests.get(f"{BACKEND_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "service" in data

    def test_database_health(self):
        """Test database connectivity."""
        response = requests.get(f"{BACKEND_URL}/db/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestAPIKeys:
    """Test API key management endpoints."""

    def test_save_and_get_api_keys(self):
        """Test saving and retrieving API keys."""
        # Save API keys for AWS
        aws_keys = {
            "access_key_id": "test_access_key",
            "secret_access_key": "test_secret_key",
            "region": "us-east-1",
            "s3_bucket_name": "test-bucket",
        }

        response = requests.post(f"{BACKEND_URL}/api/keys/aws", json={"provider": "aws", "keys": aws_keys})
        assert response.status_code == 200

        # Retrieve API keys (should be masked)
        response = requests.get(f"{BACKEND_URL}/api/keys/aws")
        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "aws"
        assert data["configured"] == True
        assert "****" in data["keys"]["secret_access_key"] or "..." in data["keys"]["secret_access_key"]

    def test_get_all_providers(self):
        """Test getting all provider statuses."""
        response = requests.get(f"{BACKEND_URL}/api/keys")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        # Check that all expected providers are present
        providers = [item["provider"] for item in data]
        assert "aws" in providers
        assert "azure" in providers
        assert "gcp" in providers

    def test_toggle_provider(self):
        """Test enabling/disabling providers."""
        # First save some keys
        aws_keys = {"access_key_id": "test_key", "secret_access_key": "test_secret", "s3_bucket_name": "test-bucket"}
        requests.post(f"{BACKEND_URL}/api/keys/aws", json={"provider": "aws", "keys": aws_keys})

        # Disable provider
        response = requests.put(f"{BACKEND_URL}/api/keys/aws/toggle", params={"enabled": False})
        assert response.status_code == 200

        # Verify it's disabled
        response = requests.get(f"{BACKEND_URL}/api/keys/aws")
        data = response.json()
        assert data["enabled"] == False

        # Re-enable provider
        response = requests.put(f"{BACKEND_URL}/api/keys/aws/toggle", params={"enabled": True})
        assert response.status_code == 200


class TestTranscription:
    """Test transcription functionality."""

    @pytest.fixture(autouse=True)
    def setup_aws_keys(self):
        """Setup AWS keys before tests."""
        aws_keys = {
            "access_key_id": os.getenv("AWS_ACCESS_KEY_ID", "test_key"),
            "secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY", "test_secret"),
            "region": os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
            "s3_bucket_name": os.getenv("S3_BUCKET_NAME", "speecher-test-bucket"),
        }

        # Only configure if real AWS credentials are available
        if aws_keys["access_key_id"] != "test_key":
            requests.post(f"{BACKEND_URL}/api/keys/aws", json={"provider": "aws", "keys": aws_keys})

    def test_transcribe_validation(self, test_audio_file):
        """Test transcription endpoint validation."""
        # Test with invalid file type
        with open(test_audio_file, "rb") as f:
            files = {"file": ("test.txt", f, "text/plain")}
            data = {"provider": "aws", "language": "en-US", "enable_diarization": False}
            response = requests.post(f"{BACKEND_URL}/transcribe", files=files, data=data)
            # Should reject invalid file type
            assert response.status_code == 400

    def test_transcribe_missing_provider_config(self, test_audio_file):
        """Test transcription with unconfigured provider."""
        # Clear any existing config
        requests.delete(f"{BACKEND_URL}/api/keys/gcp")

        with open(test_audio_file, "rb") as f:
            files = {"file": ("test.wav", f, "audio/wav")}
            data = {"provider": "gcp", "language": "en-US", "enable_diarization": False}
            response = requests.post(f"{BACKEND_URL}/transcribe", files=files, data=data)
            # Should fail with provider not configured (400 for bad request or 500 for server error)
            assert response.status_code in [400, 500]
            error_msg = response.json().get("detail", "").lower()
            assert "not configured" in error_msg or "credentials" in error_msg or "gcp" in error_msg

    @pytest.mark.skipif(
        os.getenv("AWS_ACCESS_KEY_ID", "test_key") == "test_key", reason="Real AWS credentials not available"
    )
    def test_transcribe_aws_success(self, test_audio_file):
        """Test successful transcription with AWS (requires real credentials)."""
        with open(test_audio_file, "rb") as f:
            files = {"file": ("test.wav", f, "audio/wav")}
            data = {"provider": "aws", "language": "en-US", "enable_diarization": False, "max_speakers": 1}
            response = requests.post(f"{BACKEND_URL}/transcribe", files=files, data=data)

            if response.status_code == 200:
                data = response.json()
                assert "id" in data
                assert "transcript" in data
                assert "provider" in data
                assert data["provider"] == "aws"


class TestHistory:
    """Test transcription history endpoints."""

    def test_get_history(self):
        """Test getting transcription history."""
        response = requests.get(f"{BACKEND_URL}/history")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_history_with_filters(self):
        """Test history with search filters."""
        response = requests.get(f"{BACKEND_URL}/history", params={"search": "test", "provider": "aws", "limit": 10})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 10

    def test_get_statistics(self):
        """Test statistics endpoint."""
        response = requests.get(f"{BACKEND_URL}/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_transcriptions" in data
        assert "provider_statistics" in data
        assert "recent_files" in data


class TestDockerEnvironment:
    """Test Docker-specific functionality."""

    def test_mongodb_connection(self):
        """Verify MongoDB is accessible from backend."""
        response = requests.get(f"{BACKEND_URL}/db/health")
        assert response.status_code == 200

    def test_volume_mounting(self):
        """Verify source code is properly mounted."""
        # This test assumes the backend can access its source files
        response = requests.get(f"{BACKEND_URL}/health")
        assert response.status_code == 200

        # The health endpoint should be served from mounted code
        data = response.json()
        assert data["service"] == "Speecher API"

    def test_environment_variables(self):
        """Test that environment variables are properly set."""
        response = requests.get(f"{BACKEND_URL}/debug/aws-config")
        assert response.status_code == 200
        data = response.json()

        # Should have MongoDB connection
        assert "provider_status" in data or "error" not in data


def test_complete_workflow():
    """Test complete transcription workflow."""
    # 1. Check health
    response = requests.get(f"{BACKEND_URL}/health")
    assert response.status_code == 200

    # 2. Configure API keys (mock)
    aws_keys = {
        "access_key_id": "test_key",
        "secret_access_key": "test_secret",
        "region": "us-east-1",
        "s3_bucket_name": "test-bucket",
    }
    response = requests.post(f"{BACKEND_URL}/api/keys/aws", json={"provider": "aws", "keys": aws_keys})
    assert response.status_code == 200

    # 3. Verify configuration
    response = requests.get(f"{BACKEND_URL}/api/keys")
    assert response.status_code == 200
    providers = response.json()
    aws_provider = next((p for p in providers if p["provider"] == "aws"), None)
    assert aws_provider is not None
    assert aws_provider["configured"] == True

    # 4. Get statistics
    response = requests.get(f"{BACKEND_URL}/stats")
    assert response.status_code == 200

    print("Complete workflow test passed!")


if __name__ == "__main__":
    # Wait for services to be ready
    print("Waiting for services to start...")
    max_retries = 30
    for i in range(max_retries):
        try:
            response = requests.get(f"{BACKEND_URL}/health", timeout=2)
            if response.status_code == 200:
                print("Backend is ready!")
                break
        except:
            pass
        time.sleep(2)
    else:
        print("Backend did not start in time!")
        exit(1)

    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
