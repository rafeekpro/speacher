#!/usr/bin/env python3
"""
Unit tests for backend main module endpoints.
"""

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

# Import the app
from src.backend.main import app

client = TestClient(app)


class TestBackendMain(unittest.TestCase):
    """Test cases for backend main FastAPI endpoints."""

    def test_health_endpoint(self):
        """Test health check endpoint."""
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["service"], "Speecher API")

    def test_root_endpoint(self):
        """Test root endpoint."""
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("message", data)
        self.assertIn("Speecher", data["message"])

    def test_providers_endpoint(self):
        """Test providers list endpoint."""
        response = client.get("/providers")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertIn("aws", data)
        self.assertIn("azure", data)
        self.assertIn("gcp", data)

    @patch("src.backend.main.api_keys_manager")
    def test_get_api_keys_endpoint(self, mock_manager):
        """Test getting API keys for all providers."""
        mock_manager.get_all_providers.return_value = [
            {"provider": "aws", "configured": True, "enabled": True},
            {"provider": "azure", "configured": False, "enabled": True},
            {"provider": "gcp", "configured": False, "enabled": True},
        ]

        response = client.get("/api/keys")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 3)

    @patch("src.backend.main.api_keys_manager")
    def test_get_api_keys_for_provider(self, mock_manager):
        """Test getting API keys for specific provider."""
        mock_manager.get_api_keys.return_value = {
            "provider": "aws",
            "configured": True,
            "enabled": True,
            "keys": {"access_key_id": "AKIA****", "secret_access_key": "****"},
        }

        response = client.get("/api/keys/aws")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["provider"], "aws")
        self.assertTrue(data["configured"])

    @patch("src.backend.main.api_keys_manager")
    def test_save_api_keys(self, mock_manager):
        """Test saving API keys."""
        mock_manager.validate_provider_config.return_value = True
        mock_manager.save_api_keys.return_value = True

        payload = {
            "provider": "aws",
            "keys": {
                "access_key_id": "AKIAIOSFODNN7EXAMPLE",
                "secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                "region": "us-east-1",
                "s3_bucket_name": "my-bucket",
            },
        }

        response = client.post("/api/keys/aws", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])

    @patch("src.backend.main.api_keys_manager")
    def test_delete_api_keys(self, mock_manager):
        """Test deleting API keys."""
        mock_manager.delete_api_keys.return_value = True

        response = client.delete("/api/keys/aws")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])

    @patch("src.backend.main.api_keys_manager")
    def test_toggle_provider(self, mock_manager):
        """Test toggling provider enabled status."""
        mock_manager.toggle_provider.return_value = True

        response = client.put("/api/keys/aws/toggle?enabled=false")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])

    def test_transcribe_missing_file(self):
        """Test transcribe endpoint without file."""
        response = client.post("/transcribe", data={"provider": "aws"})
        self.assertEqual(response.status_code, 422)  # FastAPI returns 422 for validation errors
        data = response.json()
        self.assertIn("detail", data)

    def test_transcribe_invalid_provider(self):
        """Test transcribe with invalid provider."""
        # Create a dummy file
        files = {"file": ("test.wav", b"dummy content", "audio/wav")}
        data = {"provider": "invalid_provider"}

        response = client.post("/transcribe", files=files, data=data)
        self.assertEqual(response.status_code, 400)

    def test_history_endpoint(self):
        """Test history endpoint."""
        with patch("src.backend.main.transcriptions_collection") as mock_collection:
            mock_collection.find.return_value.sort.return_value.limit.return_value = []

            response = client.get("/history")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIsInstance(data, list)

    def test_history_with_filters(self):
        """Test history endpoint with filters."""
        with patch("src.backend.main.transcriptions_collection") as mock_collection:
            mock_collection.find.return_value.sort.return_value.limit.return_value = []

            response = client.get("/history?search=test&provider=aws&limit=5")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIsInstance(data, list)

    def test_stats_endpoint(self):
        """Test statistics endpoint."""
        with patch("src.backend.main.transcriptions_collection") as mock_collection:
            mock_collection.count_documents.return_value = 10
            mock_collection.aggregate.return_value = [{"_id": "aws", "count": 5, "total_duration": 300}]
            mock_collection.find.return_value.sort.return_value.limit.return_value = []

            response = client.get("/stats")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("total_transcriptions", data)
            self.assertIn("provider_statistics", data)

    def test_db_health_endpoint(self):
        """Test database health check."""
        with patch("src.backend.main.db") as mock_db:
            mock_db.command.return_value = {"ok": 1}

            response = client.get("/db/health")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "healthy")

    def test_debug_aws_config(self):
        """Test debug AWS configuration endpoint."""
        response = client.get("/debug/aws-config")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Should return config status
        self.assertIsInstance(data, dict)


if __name__ == "__main__":
    unittest.main()
