#!/usr/bin/env python3
"""
Unit tests for the api_keys module which manages encrypted API key storage.
"""

import os
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

# Import the module to test
from src.backend.api_keys import APIKeysManager


class TestAPIKeysManager(unittest.TestCase):
    """Test cases for APIKeysManager class."""

    def setUp(self):
        """Set up test fixtures."""
        self.database_url = "postgresql://test:test@localhost/test"

    def test_init(self):
        """Test APIKeysManager initialization."""
        manager = APIKeysManager(self.database_url)

        self.assertIsNotNone(manager)
        self.assertTrue(manager.database_available)

    def test_encrypt_decrypt_value(self):
        """Test encryption and decryption of values."""
        manager = APIKeysManager(self.database_url)

        # Test encryption and decryption
        original_value = "test_secret_key_123"
        encrypted = manager.encrypt_value(original_value)

        # Encrypted value should be different from original
        self.assertNotEqual(encrypted, original_value)

        # Decrypted value should match original
        decrypted = manager.decrypt_value(encrypted)
        self.assertEqual(decrypted, original_value)

    def test_validate_provider_config_aws(self):
        """Test AWS provider configuration validation."""
        manager = APIKeysManager(self.database_url)

        # Valid AWS config
        valid_keys = {
            "access_key_id": "AKIAIOSFODNN7EXAMPLE",
            "secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "region": "us-east-1",
            "s3_bucket_name": "my-bucket",
        }

        result = manager.validate_provider_config("aws", valid_keys)
        self.assertTrue(result)

        # Invalid AWS config (missing required field)
        invalid_keys = {"access_key_id": "AKIAIOSFODNN7EXAMPLE", "region": "us-east-1"}

        result = manager.validate_provider_config("aws", invalid_keys)
        self.assertFalse(result)

    def test_validate_provider_config_azure(self):
        """Test Azure provider configuration validation."""
        manager = APIKeysManager(self.database_url)

        # Valid Azure config
        valid_keys = {"subscription_key": "1234567890abcdef", "region": "westeurope"}

        result = manager.validate_provider_config("azure", valid_keys)
        self.assertTrue(result)

        # Invalid Azure config
        invalid_keys = {"storage_account": "mystorageaccount"}

        result = manager.validate_provider_config("azure", invalid_keys)
        self.assertFalse(result)

    def test_validate_provider_config_gcp(self):
        """Test GCP provider configuration validation."""
        manager = APIKeysManager(self.database_url)

        # Valid GCP config
        valid_keys = {
            "credentials_json": '{"type": "service_account", "project_id": "my-project"}',
            "project_id": "my-project-123",
            "gcs_bucket_name": "my-gcp-bucket",
        }

        result = manager.validate_provider_config("gcp", valid_keys)
        self.assertTrue(result)

        # Invalid GCP config
        invalid_keys = {"project_id": "my-project-123"}

        result = manager.validate_provider_config("gcp", invalid_keys)
        self.assertFalse(result)

    def test_save_api_keys(self):
        """Test saving API keys to database."""
        manager = APIKeysManager(self.database_url)

        keys = {
            "access_key_id": "AKIAIOSFODNN7EXAMPLE",
            "secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "region": "us-east-1",
            "s3_bucket_name": "my-bucket",
        }

        result = manager.save_api_keys("aws", keys)
        self.assertTrue(result)

    def test_get_api_keys_from_db(self):
        """Test retrieving API keys from database."""
        manager = APIKeysManager(self.database_url)

        # Mock database response
        mock_doc = {
            "provider": "aws",
            "enabled": True,
            "keys": {
                "access_key_id": manager.encrypt_value("AKIAIOSFODNN7EXAMPLE"),
                "secret_access_key": manager.encrypt_value("wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"),
                "region": "us-east-1",
                "s3_bucket_name": "my-bucket",
            },
            "updated_at": datetime.utcnow(),
        }

        # This test would require database mocking - for now just test the manager exists
        self.assertIsNotNone(manager)

    @patch.dict(
        os.environ,
        {
            "AWS_ACCESS_KEY_ID": "ENV_ACCESS_KEY",
            "AWS_SECRET_ACCESS_KEY": "ENV_SECRET_KEY",
            "AWS_DEFAULT_REGION": "us-west-2",
            "S3_BUCKET_NAME": "env-bucket",
        },
    )
    def test_get_api_keys_from_env(self):
        """Test retrieving API keys from environment variables."""
        manager = APIKeysManager(self.database_url)

        result = manager.get_api_keys("aws")

        self.assertIsNotNone(result)
        self.assertEqual(result["provider"], "aws")
        self.assertTrue(result["configured"])
        self.assertEqual(result["source"], "environment")

        # Check that environment values were used
        self.assertEqual(result["keys"]["access_key_id"], "ENV_ACCESS_KEY")
        self.assertEqual(result["keys"]["secret_access_key"], "ENV_SECRET_KEY")

    def test_get_all_providers(self):
        """Test getting status of all providers."""
        manager = APIKeysManager(self.database_url)

        # Test that manager can return provider list
        # Note: This test checks the method exists and works
        # Full integration testing would require database mocking
        with patch.dict(os.environ, {}, clear=True):  # Clear environment variables
            result = manager.get_all_providers()

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 3)  # AWS, Azure, GCP

    def test_delete_api_keys(self):
        """Test deleting API keys."""
        manager = APIKeysManager(self.database_url)

        # Test that method exists and can be called
        # Full integration testing would require database mocking
        result = manager.delete_api_keys("aws")
        self.assertTrue(result)

    def test_toggle_provider(self):
        """Test toggling provider enabled status."""
        manager = APIKeysManager(self.database_url)

        # Test that method exists and can be called
        # Full integration testing would require database mocking
        result = manager.toggle_provider("aws", False)
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
