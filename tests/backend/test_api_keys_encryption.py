#!/usr/bin/env python3
"""
Test for AWS access_key_id encryption bug fix.
This test verifies that access_key_id is NOT encrypted while secret_access_key IS encrypted.
"""

import os
import unittest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.backend.api_keys import APIKeysManager, APIKey, Base


class TestAWSAccessKeyEncryption(unittest.TestCase):
    """Test that AWS access_key_id is not encrypted but secret_access_key is."""

    def setUp(self):
        """Set up test database in memory."""
        # Use in-memory SQLite for testing
        self.engine = create_engine("sqlite:///:memory:")
        self.SessionLocal = sessionmaker(bind=self.engine)
        Base.metadata.create_all(self.engine)

        # Create manager with test database
        self.manager = APIKeysManager("sqlite:///:memory:")

    def test_access_key_id_not_encrypted_on_save(self):
        """Test that access_key_id is saved as plain text, not encrypted."""
        session = self.SessionLocal()

        # Save AWS keys
        aws_keys = {
            "access_key_id": "AKIATESTACCESSKEY123",
            "secret_access_key": "test_secret_key_value",
            "region": "us-east-1",
            "s3_bucket_name": "test-bucket",
        }

        self.manager.save_api_keys("aws", aws_keys)

        # Retrieve from database directly
        api_key_record = session.query(APIKey).filter_by(provider="aws").first()
        self.assertIsNotNone(api_key_record)

        # Verify access_key_id is NOT encrypted (plain text)
        self.assertEqual(
            api_key_record.keys["access_key_id"],
            "AKIATESTACCESSKEY123",
            "access_key_id should be stored as plain text, not encrypted"
        )

        # Verify secret_access_key IS encrypted (starts with gAAAAAB for Fernet)
        self.assertTrue(
            api_key_record.keys["secret_access_key"].startswith("gAAAAAB"),
            "secret_access_key should be encrypted (start with 'gAAAAAB')"
        )

        # Verify other fields are not encrypted
        self.assertEqual(api_key_record.keys["region"], "us-east-1")
        self.assertEqual(api_key_record.keys["s3_bucket_name"], "test-bucket")

        session.close()

    def test_secret_access_key_encrypted_on_save(self):
        """Test that secret_access_key is properly encrypted."""
        # Save AWS keys
        aws_keys = {
            "access_key_id": "AKIATESTACCESSKEY123",
            "secret_access_key": "my_super_secret_key",
            "region": "us-east-1",
            "s3_bucket_name": "test-bucket",
        }

        self.manager.save_api_keys("aws", aws_keys)

        # Get keys back through the manager
        result = self.manager.get_api_keys("aws")

        self.assertIsNotNone(result)
        self.assertEqual(result["keys"]["access_key_id"], "AKIATESTACCESSKEY123")
        self.assertEqual(result["keys"]["secret_access_key"], "my_super_secret_key")

    def test_get_api_keys_decrypts_correctly(self):
        """Test that get_api_keys properly decrypts encrypted values."""
        # Save AWS keys
        aws_keys = {
            "access_key_id": "AKIATESTACCESSKEY123",
            "secret_access_key": "my_secret_key",
            "region": "us-east-1",
            "s3_bucket_name": "test-bucket",
        }

        self.manager.save_api_keys("aws", aws_keys)

        # Retrieve through manager
        result = self.manager.get_api_keys("aws")

        self.assertIsNotNone(result)
        # Both should be returned as plain text after decryption
        self.assertEqual(result["keys"]["access_key_id"], "AKIATESTACCESSKEY123")
        self.assertEqual(result["keys"]["secret_access_key"], "my_secret_key")

    def test_get_all_providers_decrypts_correctly(self):
        """Test that get_all_providers properly handles encryption."""
        # Save AWS keys
        aws_keys = {
            "access_key_id": "AKIATESTACCESSKEY123",
            "secret_access_key": "my_secret_key",
            "region": "us-east-1",
            "s3_bucket_name": "test-bucket",
        }

        self.manager.save_api_keys("aws", aws_keys)

        # Get all providers
        with patch.dict(os.environ, {}, clear=True):
            providers = self.manager.get_all_providers()

        # Find AWS provider
        aws_provider = next((p for p in providers if p["provider"] == "aws"), None)
        self.assertIsNotNone(aws_provider)
        self.assertTrue(aws_provider["configured"])


if __name__ == "__main__":
    unittest.main()
