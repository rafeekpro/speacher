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
        self.mongodb_uri = "mongodb://test:test@localhost:27017/test"
        self.db_name = "test_db"

        # Mock MongoDB client
        self.mock_client = MagicMock()
        self.mock_db = MagicMock()
        self.mock_collection = MagicMock()

    @patch("src.backend.api_keys.MongoClient")
    def test_init(self, mock_mongo_client):
        """Test APIKeysManager initialization."""
        mock_client = MagicMock()
        mock_client.server_info.return_value = {"version": "4.4.0"}
        mock_client.__getitem__.return_value = self.mock_db
        self.mock_db.__getitem__.return_value = self.mock_collection
        mock_mongo_client.return_value = mock_client

        manager = APIKeysManager(self.mongodb_uri, self.db_name)

        self.assertIsNotNone(manager)
        self.assertTrue(manager.mongodb_available)
        mock_mongo_client.assert_called_once_with(self.mongodb_uri, serverSelectionTimeoutMS=2000)

    @patch("src.backend.api_keys.MongoClient")
    def test_encrypt_decrypt_value(self, mock_mongo_client):
        """Test encryption and decryption of values."""
        mock_client = MagicMock()
        mock_client.server_info.return_value = {"version": "4.4.0"}
        mock_client.__getitem__.return_value = self.mock_db
        self.mock_db.__getitem__.return_value = self.mock_collection
        mock_mongo_client.return_value = mock_client

        manager = APIKeysManager(self.mongodb_uri, self.db_name)

        # Test encryption and decryption
        original_value = "test_secret_key_123"
        encrypted = manager.encrypt_value(original_value)

        # Encrypted value should be different from original
        self.assertNotEqual(encrypted, original_value)

        # Decrypted value should match original
        decrypted = manager.decrypt_value(encrypted)
        self.assertEqual(decrypted, original_value)

    @patch("src.backend.api_keys.MongoClient")
    def test_validate_provider_config_aws(self, mock_mongo_client):
        """Test AWS provider configuration validation."""
        mock_mongo_client.return_value = self.mock_client
        self.mock_client.__getitem__.return_value = self.mock_db
        self.mock_db.__getitem__.return_value = self.mock_collection

        manager = APIKeysManager(self.mongodb_uri, self.db_name)

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

    @patch("src.backend.api_keys.MongoClient")
    def test_validate_provider_config_azure(self, mock_mongo_client):
        """Test Azure provider configuration validation."""
        mock_mongo_client.return_value = self.mock_client
        self.mock_client.__getitem__.return_value = self.mock_db
        self.mock_db.__getitem__.return_value = self.mock_collection

        manager = APIKeysManager(self.mongodb_uri, self.db_name)

        # Valid Azure config
        valid_keys = {"subscription_key": "1234567890abcdef", "region": "westeurope"}

        result = manager.validate_provider_config("azure", valid_keys)
        self.assertTrue(result)

        # Invalid Azure config
        invalid_keys = {"storage_account": "mystorageaccount"}

        result = manager.validate_provider_config("azure", invalid_keys)
        self.assertFalse(result)

    @patch("src.backend.api_keys.MongoClient")
    def test_validate_provider_config_gcp(self, mock_mongo_client):
        """Test GCP provider configuration validation."""
        mock_mongo_client.return_value = self.mock_client
        self.mock_client.__getitem__.return_value = self.mock_db
        self.mock_db.__getitem__.return_value = self.mock_collection

        manager = APIKeysManager(self.mongodb_uri, self.db_name)

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

    @patch("src.backend.api_keys.MongoClient")
    def test_save_api_keys(self, mock_mongo_client):
        """Test saving API keys to MongoDB."""
        mock_mongo_client.return_value = self.mock_client
        self.mock_client.__getitem__.return_value = self.mock_db
        self.mock_db.__getitem__.return_value = self.mock_collection

        # Mock successful update
        self.mock_collection.replace_one.return_value = MagicMock(modified_count=1)

        manager = APIKeysManager(self.mongodb_uri, self.db_name)

        keys = {
            "access_key_id": "AKIAIOSFODNN7EXAMPLE",
            "secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "region": "us-east-1",
            "s3_bucket_name": "my-bucket",
        }

        result = manager.save_api_keys("aws", keys)
        self.assertTrue(result)

        # Verify MongoDB was called
        self.mock_collection.replace_one.assert_called_once()
        call_args = self.mock_collection.replace_one.call_args

        # Check that provider filter was used
        self.assertEqual(call_args[0][0]["provider"], "aws")

        # Check that upsert was True
        self.assertTrue(call_args[1]["upsert"])

    @patch("src.backend.api_keys.MongoClient")
    def test_get_api_keys_from_db(self, mock_mongo_client):
        """Test retrieving API keys from MongoDB."""
        mock_mongo_client.return_value = self.mock_client
        self.mock_client.__getitem__.return_value = self.mock_db
        self.mock_db.__getitem__.return_value = self.mock_collection

        manager = APIKeysManager(self.mongodb_uri, self.db_name)

        # Mock MongoDB response
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

        self.mock_collection.find_one.return_value = mock_doc

        result = manager.get_api_keys("aws")

        self.assertIsNotNone(result)
        self.assertEqual(result["provider"], "aws")
        self.assertTrue(result["configured"])
        self.assertTrue(result["enabled"])

        # Check that sensitive values are decrypted (not masked)
        self.assertEqual(result["keys"]["secret_access_key"], "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")

        # Verify MongoDB was queried
        self.mock_collection.find_one.assert_called_once_with({"provider": "aws"})

    @patch.dict(
        os.environ,
        {
            "AWS_ACCESS_KEY_ID": "ENV_ACCESS_KEY",
            "AWS_SECRET_ACCESS_KEY": "ENV_SECRET_KEY",
            "AWS_DEFAULT_REGION": "us-west-2",
            "S3_BUCKET_NAME": "env-bucket",
        },
    )
    @patch("src.backend.api_keys.MongoClient")
    def test_get_api_keys_from_env(self, mock_mongo_client):
        """Test retrieving API keys from environment variables."""
        mock_mongo_client.return_value = self.mock_client
        self.mock_client.__getitem__.return_value = self.mock_db
        self.mock_db.__getitem__.return_value = self.mock_collection

        # Mock no result from MongoDB
        self.mock_collection.find_one.return_value = None

        manager = APIKeysManager(self.mongodb_uri, self.db_name)

        result = manager.get_api_keys("aws")

        self.assertIsNotNone(result)
        self.assertEqual(result["provider"], "aws")
        self.assertTrue(result["configured"])
        self.assertEqual(result["source"], "environment")

        # Check that environment values were used
        self.assertEqual(result["keys"]["access_key_id"], "ENV_ACCESS_KEY")
        self.assertEqual(result["keys"]["secret_access_key"], "ENV_SECRET_KEY")

    @patch("src.backend.api_keys.MongoClient")
    def test_get_all_providers(self, mock_mongo_client):
        """Test getting status of all providers."""
        mock_mongo_client.return_value = self.mock_client
        self.mock_client.__getitem__.return_value = self.mock_db
        self.mock_db.__getitem__.return_value = self.mock_collection

        manager = APIKeysManager(self.mongodb_uri, self.db_name)

        # Mock MongoDB responses for find() which returns all providers
        self.mock_collection.find.return_value = [
            {
                "provider": "aws",
                "enabled": True,
                "keys": {
                    "access_key_id": manager.encrypt_value("AKIAIOSFODNN7EXAMPLE"),
                    "secret_access_key": manager.encrypt_value("secret"),
                    "region": "us-east-1",
                    "s3_bucket_name": "bucket",
                },
            }
        ]

        with patch.dict(os.environ, {}, clear=True):  # Clear environment variables
            result = manager.get_all_providers()

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 3)  # AWS, Azure, GCP

        # Find AWS provider in results
        aws_provider = next((p for p in result if p["provider"] == "aws"), None)
        self.assertIsNotNone(aws_provider)
        self.assertTrue(aws_provider["configured"])
        self.assertTrue(aws_provider["enabled"])

        # Find Azure provider (should not be configured)
        azure_provider = next((p for p in result if p["provider"] == "azure"), None)
        self.assertIsNotNone(azure_provider)
        self.assertFalse(azure_provider["configured"])

    @patch("src.backend.api_keys.MongoClient")
    def test_delete_api_keys(self, mock_mongo_client):
        """Test deleting API keys."""
        mock_mongo_client.return_value = self.mock_client
        self.mock_client.__getitem__.return_value = self.mock_db
        self.mock_db.__getitem__.return_value = self.mock_collection

        # Mock successful deletion
        self.mock_collection.delete_one.return_value = MagicMock(deleted_count=1)

        manager = APIKeysManager(self.mongodb_uri, self.db_name)

        result = manager.delete_api_keys("aws")
        self.assertTrue(result)

        # Verify MongoDB delete was called
        self.mock_collection.delete_one.assert_called_once_with({"provider": "aws"})

    @patch("src.backend.api_keys.MongoClient")
    def test_toggle_provider(self, mock_mongo_client):
        """Test toggling provider enabled status."""
        mock_mongo_client.return_value = self.mock_client
        self.mock_client.__getitem__.return_value = self.mock_db
        self.mock_db.__getitem__.return_value = self.mock_collection

        # Mock successful update
        self.mock_collection.update_one.return_value = MagicMock(modified_count=1)

        manager = APIKeysManager(self.mongodb_uri, self.db_name)

        result = manager.toggle_provider("aws", False)
        self.assertTrue(result)

        # Verify MongoDB update was called
        self.mock_collection.update_one.assert_called_once()
        call_args = self.mock_collection.update_one.call_args

        # Check that provider filter was used
        self.assertEqual(call_args[0][0]["provider"], "aws")

        # Check that enabled was set to False
        self.assertFalse(call_args[0][1]["$set"]["enabled"])


if __name__ == "__main__":
    unittest.main()
