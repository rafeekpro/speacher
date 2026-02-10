#!/usr/bin/env python3
"""
Unit tests for the cloud_wrappers module which provides backend API wrappers for cloud services.
"""

import unittest
from unittest.mock import MagicMock, mock_open, patch

# Import the module to test
import src.backend.cloud_wrappers as cloud_wrappers


class TestCloudWrappersModule(unittest.TestCase):
    """Test cases for cloud_wrappers module functions."""

    def setUp(self):
        """Set up test fixtures."""
        # Test constants
        self.test_file_path = "/tmp/test_audio.wav"
        self.storage_account = "test_storage_account"
        self.storage_key = "test_storage_key"
        self.container_name = "test-container"
        self.blob_name = "test-audio.wav"
        self.bucket_name = "test-bucket"
        self.project_id = "test-project-123"

    # Azure wrappers tests
    @patch("azure.storage.blob.BlobServiceClient.from_connection_string")
    def test_upload_to_blob_success(self, mock_blob_service_client):
        """Test successful upload to Azure Blob Storage."""
        # Setup mock
        mock_blob_client = MagicMock()
        mock_blob_client.url = (
            f"https://{self.storage_account}.blob.core.windows.net/{self.container_name}/{self.blob_name}"
        )

        mock_service_client = MagicMock()
        mock_service_client.get_blob_client.return_value = mock_blob_client

        mock_blob_service_client.return_value = mock_service_client

        with patch("builtins.open", mock_open(read_data=b"dummy_wav_data")):
            result = cloud_wrappers.upload_to_blob(
                self.test_file_path, self.storage_account, self.storage_key, self.container_name, self.blob_name
            )

            self.assertIsNotNone(result)
            self.assertEqual(result, mock_blob_client.url)

            # Verify connection string
            expected_connection = f"DefaultEndpointsProtocol=https;AccountName={self.storage_account};AccountKey={self.storage_key};EndpointSuffix=core.windows.net"
            mock_blob_service_client.assert_called_once_with(expected_connection)

            # Verify blob client was created with correct params
            mock_service_client.get_blob_client.assert_called_once_with(
                container=self.container_name, blob=self.blob_name
            )

            # Verify upload was called
            mock_blob_client.upload_blob.assert_called_once()

    @patch("azure.storage.blob.BlobServiceClient.from_connection_string")
    def test_upload_to_blob_error(self, mock_blob_service_client):
        """Test error handling when uploading to Azure Blob."""
        # Setup mock to raise exception
        mock_blob_service_client.side_effect = Exception("Connection error")

        result = cloud_wrappers.upload_to_blob(
            self.test_file_path, self.storage_account, self.storage_key, self.container_name, self.blob_name
        )

        self.assertIsNone(result)

    def test_transcribe_from_blob(self):
        """Test transcribing from Azure Blob."""
        blob_url = f"https://{self.storage_account}.blob.core.windows.net/{self.container_name}/{self.blob_name}"

        result = cloud_wrappers.transcribe_from_blob(
            blob_url, language="en-US", enable_diarization=True, max_speakers=2
        )

        self.assertIsNotNone(result)
        self.assertIn("displayText", result)
        self.assertIn("duration", result)

    @patch("azure.storage.blob.BlobServiceClient.from_connection_string")
    def test_delete_blob_success(self, mock_blob_service_client):
        """Test successful blob deletion from Azure Storage."""
        # Setup mock
        mock_blob_client = MagicMock()
        mock_service_client = MagicMock()
        mock_service_client.get_blob_client.return_value = mock_blob_client

        mock_blob_service_client.return_value = mock_service_client

        result = cloud_wrappers.delete_blob(self.storage_account, self.storage_key, self.container_name, self.blob_name)

        self.assertTrue(result)
        mock_blob_client.delete_blob.assert_called_once()

    @patch("azure.storage.blob.BlobServiceClient.from_connection_string")
    def test_delete_blob_error(self, mock_blob_service_client):
        """Test error handling when deleting blob."""
        # Setup mock to raise exception
        mock_blob_service_client.side_effect = Exception("Delete error")

        result = cloud_wrappers.delete_blob(self.storage_account, self.storage_key, self.container_name, self.blob_name)

        self.assertFalse(result)

    # GCP wrappers tests
    @patch("google.cloud.storage.Client")
    def test_upload_to_gcs_success(self, mock_storage_client):
        """Test successful upload to Google Cloud Storage."""
        # Setup mock
        mock_bucket = MagicMock()
        mock_blob = MagicMock()

        mock_client = MagicMock()
        mock_client.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        mock_storage_client.return_value = mock_client

        result = cloud_wrappers.upload_to_gcs(self.test_file_path, self.bucket_name, "test-audio.wav")

        self.assertIsNotNone(result)
        self.assertTrue(result.startswith("gs://"))
        self.assertEqual(result, f"gs://{self.bucket_name}/test-audio.wav")

        mock_storage_client.assert_called_once_with()
        mock_client.bucket.assert_called_once_with(self.bucket_name)
        mock_bucket.blob.assert_called_once_with("test-audio.wav")
        mock_blob.upload_from_filename.assert_called_once_with(self.test_file_path)

    @patch("google.cloud.storage.Client")
    def test_upload_to_gcs_error(self, mock_storage_client):
        """Test error handling when uploading to GCS."""
        # Setup mock to raise exception
        mock_storage_client.side_effect = Exception("Upload error")

        result = cloud_wrappers.upload_to_gcs(self.test_file_path, self.bucket_name, "test-audio.wav")

        self.assertIsNone(result)

    @patch("google.cloud.speech.SpeechClient")
    def test_transcribe_from_gcs(self, mock_speech_client):
        """Test transcribing from Google Cloud Storage."""
        # Setup mock
        mock_client = MagicMock()
        mock_operation = MagicMock()
        mock_response = MagicMock()

        mock_result = MagicMock()
        mock_alternative = MagicMock()
        mock_alternative.transcript = "Test transcription"
        mock_result.alternatives = [mock_alternative]
        mock_response.results = [mock_result]

        mock_operation.result.return_value = mock_response
        mock_client.long_running_recognize.return_value = mock_operation
        mock_speech_client.return_value = mock_client

        gcs_uri = f"gs://{self.bucket_name}/test-audio.wav"

        result = cloud_wrappers.transcribe_from_gcs(gcs_uri, language="en-US", enable_diarization=True, max_speakers=2)

        self.assertIsNotNone(result)
        self.assertIn("results", result)
        self.assertIsInstance(result["results"], list)
        self.assertGreater(len(result["results"]), 0)

    @patch("google.cloud.storage.Client")
    def test_delete_from_gcs_success(self, mock_storage_client):
        """Test successful deletion from GCS."""
        # Setup mock
        mock_bucket = MagicMock()
        mock_blob = MagicMock()

        mock_client = MagicMock()
        mock_client.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        mock_storage_client.return_value = mock_client

        result = cloud_wrappers.delete_from_gcs(self.bucket_name, "test-audio.wav")

        self.assertTrue(result)
        mock_blob.delete.assert_called_once()

    @patch("google.cloud.storage.Client")
    def test_delete_from_gcs_error(self, mock_storage_client):
        """Test error handling when deleting from GCS."""
        # Setup mock to raise exception
        mock_storage_client.side_effect = Exception("Delete error")

        result = cloud_wrappers.delete_from_gcs(self.bucket_name, "test-audio.wav")

        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
