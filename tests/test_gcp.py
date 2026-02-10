#!/usr/bin/env python3
"""
Unit tests for the GCP module which handles interactions with Google Cloud Platform services.
"""

import os
import unittest
import uuid
from unittest.mock import MagicMock, mock_open, patch

# Import the module to test
import src.speecher.gcp as gcp

# Import test utilities
from tests.test_utils import create_sample_wav_file, get_sample_transcription_data, setup_test_data_dir


class TestGCPModule(unittest.TestCase):
    """Test cases for GCP module functions."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_data_dir = setup_test_data_dir()
        self.sample_wav_path = create_sample_wav_file()
        self.sample_transcription_data = get_sample_transcription_data()

        # Test constants
        self.project_id = "test-project-123"
        self.bucket_name = f"test-bucket-{str(uuid.uuid4())[:8]}"
        self.job_name = f"test-job-{str(uuid.uuid4())[:8]}"

    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up test files
        if self.sample_wav_path.exists():
            self.sample_wav_path.unlink()

    def test_create_unique_bucket_name(self):
        """Test creating unique bucket name."""
        name1 = gcp.create_unique_bucket_name()
        name2 = gcp.create_unique_bucket_name()

        # Names should be different
        self.assertNotEqual(name1, name2)

        # Names should start with default prefix
        self.assertTrue(name1.startswith("audio-transcription-"))

        # Names should be lowercase
        self.assertEqual(name1, name1.lower())

        # Test with custom base name
        custom_name = gcp.create_unique_bucket_name("my-custom-bucket")
        self.assertTrue(custom_name.startswith("my-custom-bucket-"))

    @patch("google.cloud.storage.Client")
    def test_create_storage_bucket_success(self, mock_storage_client_class):
        """Test successful bucket creation in GCS."""
        # Setup mock
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_client.lookup_bucket.return_value = None  # Bucket doesn't exist
        mock_client.create_bucket.return_value = mock_bucket
        mock_storage_client_class.return_value = mock_client

        result = gcp.create_storage_bucket(self.bucket_name, self.project_id)

        self.assertTrue(result)
        mock_storage_client_class.assert_called_once_with(project=self.project_id)
        mock_client.lookup_bucket.assert_called_once_with(self.bucket_name)
        mock_client.create_bucket.assert_called_once_with(self.bucket_name, location="us-central1")

    @patch("google.cloud.storage.Client")
    def test_create_storage_bucket_already_exists(self, mock_storage_client_class):
        """Test bucket creation when bucket already exists."""
        # Setup mock - bucket already exists
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_client.lookup_bucket.return_value = mock_bucket  # Bucket exists
        mock_storage_client_class.return_value = mock_client

        result = gcp.create_storage_bucket(self.bucket_name, self.project_id)

        # Should still return True for existing bucket
        self.assertTrue(result)
        # Should not try to create bucket if it exists
        mock_client.create_bucket.assert_not_called()

    @patch("google.cloud.storage.Client")
    def test_create_storage_bucket_error(self, mock_storage_client_class):
        """Test error handling when creating bucket."""
        # Setup mock to raise general exception
        mock_client = MagicMock()
        mock_client.lookup_bucket.return_value = None  # Bucket doesn't exist
        mock_client.create_bucket.side_effect = Exception("API Error")
        mock_storage_client_class.return_value = mock_client

        result = gcp.create_storage_bucket(self.bucket_name, self.project_id)

        self.assertFalse(result)

    @patch("google.cloud.storage.Client")
    def test_upload_file_to_storage_success(self, mock_storage_client_class):
        """Test successful file upload to GCS."""
        # Setup mock
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_blob = MagicMock()

        mock_client.get_bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob
        mock_blob.public_url = f"https://storage.googleapis.com/{self.bucket_name}/test.wav"

        mock_storage_client_class.return_value = mock_client

        result = gcp.upload_file_to_storage(str(self.sample_wav_path), self.bucket_name, self.project_id)

        self.assertIsNotNone(result)
        self.assertTrue(result.startswith("gs://"))
        self.assertEqual(result, f"gs://{self.bucket_name}/{os.path.basename(str(self.sample_wav_path))}")

        mock_client.get_bucket.assert_called_once_with(self.bucket_name)
        expected_blob_name = os.path.basename(str(self.sample_wav_path))
        mock_bucket.blob.assert_called_once_with(expected_blob_name)
        mock_blob.upload_from_filename.assert_called_once_with(str(self.sample_wav_path))
        mock_blob.make_public.assert_called_once()

    @patch("google.cloud.storage.Client")
    def test_upload_file_to_storage_with_custom_name(self, mock_storage_client_class):
        """Test uploading file with custom blob name."""
        # Setup mock
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_blob = MagicMock()

        mock_client.get_bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob
        mock_blob.public_url = f"https://storage.googleapis.com/{self.bucket_name}/custom-audio.wav"

        mock_storage_client_class.return_value = mock_client

        custom_blob_name = "custom-audio.wav"

        result = gcp.upload_file_to_storage(
            str(self.sample_wav_path), self.bucket_name, self.project_id, blob_name=custom_blob_name
        )

        self.assertIsNotNone(result)
        self.assertEqual(result, f"gs://{self.bucket_name}/{custom_blob_name}")
        mock_bucket.blob.assert_called_once_with(custom_blob_name)

    @patch("google.cloud.storage.Client")
    def test_upload_file_to_storage_error(self, mock_storage_client_class):
        """Test error handling when uploading file."""
        # Setup mock to raise exception
        mock_client = MagicMock()
        mock_client.get_bucket.side_effect = Exception("Upload error")
        mock_storage_client_class.return_value = mock_client

        result = gcp.upload_file_to_storage(str(self.sample_wav_path), self.bucket_name, self.project_id)

        self.assertIsNone(result)

    @patch("google.cloud.speech.SpeechClient")
    def test_start_transcription_job_success(self, mock_speech_client_class):
        """Test starting a transcription job."""
        # Setup mock
        mock_client = MagicMock()
        mock_operation = MagicMock()
        mock_operation.name = "operations/12345"

        mock_client.long_running_recognize.return_value = mock_operation
        mock_speech_client_class.return_value = mock_client

        gcs_uri = f"gs://{self.bucket_name}/test.wav"

        result = gcp.start_transcription_job(
            gcs_uri, self.project_id, job_name=self.job_name, language_code="en-US", max_speakers=2
        )

        self.assertIsNotNone(result)
        self.assertEqual(result["name"], "operations/12345")

        # Verify the client was called
        mock_speech_client_class.assert_called_once()
        mock_client.long_running_recognize.assert_called_once()

    @patch("google.cloud.speech.SpeechClient")
    def test_start_transcription_job_error(self, mock_speech_client_class):
        """Test error handling when starting transcription job."""
        # Setup mock to raise exception
        mock_client = MagicMock()
        mock_client.long_running_recognize.side_effect = Exception("API Error")
        mock_speech_client_class.return_value = mock_client

        gcs_uri = f"gs://{self.bucket_name}/test.wav"

        result = gcp.start_transcription_job(gcs_uri, self.project_id)

        self.assertIsNone(result)

    @patch("google.cloud.speech.SpeechClient")
    def test_get_transcription_job_status(self, mock_speech_client_class):
        """Test getting transcription job status."""
        # Setup mock
        mock_client = MagicMock()
        mock_operations_client = MagicMock()
        mock_operation = MagicMock()

        mock_operation.done = True
        mock_operation.name = "operations/12345"

        mock_operations_client.get_operation.return_value = mock_operation
        mock_client.transport._operations_client = mock_operations_client
        mock_speech_client_class.return_value = mock_client

        result = gcp.get_transcription_job_status("operations/12345", self.project_id)

        self.assertIsNotNone(result)
        self.assertTrue(result["done"])

        mock_operations_client.get_operation.assert_called_once()

    @patch("src.speecher.gcp.get_transcription_job_status")
    @patch("time.sleep")
    def test_wait_for_job_completion(self, mock_sleep, mock_get_status):
        """Test waiting for job completion."""
        # First call returns pending, second returns complete
        mock_get_status.side_effect = [
            {"done": False, "operation": "operations/12345"},
            {"done": True, "operation": "operations/12345", "response": {}},
        ]

        result = gcp.wait_for_job_completion("operations/12345", self.project_id, poll_interval=1)

        self.assertIsNotNone(result)
        self.assertTrue(result["done"])
        self.assertEqual(mock_get_status.call_count, 2)
        mock_sleep.assert_called_once_with(1)

    @patch("google.cloud.speech.SpeechClient")
    def test_download_transcription_result_success(self, mock_speech_client_class):
        """Test downloading transcription results."""
        # Setup mock
        mock_client = MagicMock()
        mock_operations_client = MagicMock()
        mock_operation = MagicMock()

        # Create mock result
        mock_result = MagicMock()
        mock_alternative = MagicMock()
        mock_alternative.transcript = "This is a test transcription."
        mock_alternative.confidence = 0.95

        mock_word1 = MagicMock()
        mock_word1.word = "This"
        mock_word1.start_time.seconds = 0
        mock_word1.start_time.nanos = 0
        mock_word1.end_time.seconds = 0
        mock_word1.end_time.nanos = 500000000

        mock_word2 = MagicMock()
        mock_word2.word = "is"
        mock_word2.start_time.seconds = 0
        mock_word2.start_time.nanos = 500000000
        mock_word2.end_time.seconds = 1
        mock_word2.end_time.nanos = 0

        mock_alternative.words = [mock_word1, mock_word2]
        mock_result.alternatives = [mock_alternative]

        mock_operation.done = True
        mock_operation.error = None  # Explicitly set error to None for success case

        # Set up operation.response (not operation.result)
        mock_response = MagicMock()
        mock_response.results = [mock_result]
        mock_operation.response = mock_response

        mock_operations_client.get_operation.return_value = mock_operation
        mock_client.transport._operations_client = mock_operations_client
        mock_speech_client_class.return_value = mock_client

        result = gcp.download_transcription_result("operations/12345", self.project_id)

        self.assertIsNotNone(result)
        self.assertIn("results", result)
        self.assertIsInstance(result["results"], dict)
        self.assertIn("transcripts", result["results"])
        self.assertIn("items", result["results"])
        self.assertGreater(len(result["results"]["transcripts"]), 0)

    @patch("google.cloud.speech.SpeechClient")
    def test_download_transcription_result_not_done(self, mock_speech_client_class):
        """Test downloading results when job is not complete."""
        # Setup mock
        mock_client = MagicMock()
        mock_operations_client = MagicMock()
        mock_operation = MagicMock()

        mock_operation.done = False

        mock_operations_client.get_operation.return_value = mock_operation
        mock_client.transport._operations_client = mock_operations_client
        mock_speech_client_class.return_value = mock_client

        result = gcp.download_transcription_result("operations/12345", self.project_id)

        self.assertIsNone(result)

    @patch("google.cloud.storage.Client")
    def test_cleanup_resources(self, mock_storage_client_class):
        """Test cleaning up GCP resources."""
        # Setup mock
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_blob = MagicMock()

        mock_client.get_bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob
        mock_bucket.list_blobs.return_value = [mock_blob]

        mock_storage_client_class.return_value = mock_client

        gcp.cleanup_resources(self.bucket_name, self.project_id, blob_name="test.wav")

        # Verify cleanup was called
        mock_blob.delete.assert_called_once()
        # When blob_name is provided, bucket should not be deleted
        mock_bucket.delete.assert_not_called()

    @patch("google.cloud.storage.Client")
    def test_delete_file_from_storage(self, mock_storage_client_class):
        """Test deleting a file from GCS."""
        # Setup mock
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_blob = MagicMock()

        mock_client.get_bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        mock_storage_client_class.return_value = mock_client

        result = gcp.delete_file_from_storage(self.bucket_name, self.project_id, "test.wav")

        self.assertTrue(result)
        mock_blob.delete.assert_called_once()

    @patch("google.cloud.storage.Client")
    def test_delete_file_from_storage_error(self, mock_storage_client_class):
        """Test error handling when deleting file."""
        # Setup mock to raise exception
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_blob.delete.side_effect = Exception("Delete error")

        mock_client.get_bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        mock_storage_client_class.return_value = mock_client

        result = gcp.delete_file_from_storage(self.bucket_name, self.project_id, "test.wav")

        self.assertFalse(result)

    def test_calculate_service_cost(self):
        """Test calculating GCP service costs."""
        # Test with 5 minutes of audio
        audio_length = 300  # seconds

        cost_info = gcp.calculate_service_cost(audio_length)

        self.assertIsInstance(cost_info, dict)
        self.assertIn("audio_length_seconds", cost_info)
        self.assertIn("audio_size_mb", cost_info)
        self.assertIn("transcribe_cost", cost_info)
        self.assertIn("storage_cost", cost_info)
        self.assertIn("total_cost", cost_info)
        self.assertIn("currency", cost_info)

        # Verify calculations
        self.assertEqual(cost_info["audio_length_seconds"], audio_length)
        self.assertGreater(cost_info["audio_size_mb"], 0)
        self.assertGreaterEqual(cost_info["transcribe_cost"], 0)
        self.assertGreaterEqual(cost_info["storage_cost"], 0)
        self.assertGreaterEqual(cost_info["total_cost"], 0)

        # Total should be sum of individual costs
        expected_total = cost_info["transcribe_cost"] + cost_info["storage_cost"] + cost_info.get("operation_cost", 0)
        self.assertAlmostEqual(cost_info["total_cost"], expected_total, places=4)

    def test_get_supported_languages(self):
        """Test getting supported languages."""
        languages = gcp.get_supported_languages()

        self.assertIsInstance(languages, dict)
        self.assertGreater(len(languages), 0)

        # Check for some common languages
        self.assertIn("pl-PL", languages)
        self.assertEqual(languages["pl-PL"], "polski")
        self.assertIn("en-US", languages)
        self.assertEqual(languages["en-US"], "angielski (USA)")
        self.assertIn("de-DE", languages)
        self.assertIn("fr-FR", languages)
        self.assertIn("es-ES", languages)

    @patch("google.cloud.speech.SpeechClient")
    def test_transcribe_short_audio_success(self, mock_speech_client_class):
        """Test transcribing short audio directly."""
        # Setup mock
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_result = MagicMock()
        mock_alternative = MagicMock()

        mock_alternative.transcript = "This is a test."
        mock_alternative.confidence = 0.95
        mock_result.alternatives = [mock_alternative]
        mock_response.results = [mock_result]

        mock_client.recognize.return_value = mock_response
        mock_speech_client_class.return_value = mock_client

        with patch("builtins.open", mock_open(read_data=b"dummy_wav_data")):
            result = gcp.transcribe_short_audio(str(self.sample_wav_path), self.project_id, language_code="en-US")

            self.assertEqual(result, "This is a test.")
            mock_client.recognize.assert_called_once()

    @patch("google.cloud.speech.SpeechClient")
    def test_transcribe_short_audio_no_results(self, mock_speech_client_class):
        """Test transcribing when no speech is recognized."""
        # Setup mock
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.results = []

        mock_client.recognize.return_value = mock_response
        mock_speech_client_class.return_value = mock_client

        with patch("builtins.open", mock_open(read_data=b"dummy_wav_data")):
            result = gcp.transcribe_short_audio(str(self.sample_wav_path), self.project_id)

            self.assertIsNone(result)

    @patch("google.cloud.speech.SpeechClient")
    def test_transcribe_short_audio_error(self, mock_speech_client_class):
        """Test error handling in short audio transcription."""
        # Setup mock to raise exception
        mock_client = MagicMock()
        mock_client.recognize.side_effect = Exception("API Error")
        mock_speech_client_class.return_value = mock_client

        with patch("builtins.open", mock_open(read_data=b"dummy_wav_data")):
            result = gcp.transcribe_short_audio(str(self.sample_wav_path), self.project_id)

            self.assertIsNone(result)

    def test_detect_audio_properties(self):
        """Test detecting audio file properties."""
        # Test with non-existent file
        result = gcp.detect_audio_properties("/non/existent/file.wav")

        self.assertIsInstance(result, dict)
        # Function should handle error gracefully
        self.assertTrue(result.get("channels", 0) >= 0)
        self.assertTrue(result.get("sample_rate", 0) >= 0)

        # Test with actual test file would require wave module
        # and proper WAV file creation


if __name__ == "__main__":
    unittest.main()
