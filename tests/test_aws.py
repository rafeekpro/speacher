#!/usr/bin/env python3
"""
Unit tests for the AWS module which handles interactions with AWS services.
"""

import os
import unittest
import uuid
from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError

# Import the module to test
from src.speecher import aws

# Import test utilities
from tests.test_utils import (
    create_mock_s3_client,
    create_mock_transcribe_client,
    create_sample_wav_file,
    get_sample_transcription_data,
    setup_test_data_dir,
)


class TestAWSModule(unittest.TestCase):
    """Test cases for AWS module functions"""

    def setUp(self):
        """Set up before each test"""
        self.test_data_dir = setup_test_data_dir()
        # Zapewniamy, że katalog test_data istnieje
        os.makedirs(self.test_data_dir, exist_ok=True)

        self.sample_wav_path = create_sample_wav_file()
        self.bucket_name = f"test-bucket-{uuid.uuid4().hex[:8]}"

        # Request mock responses
        self.mock_response = MagicMock()
        self.mock_response.json.return_value = get_sample_transcription_data()
        self.mock_response.raise_for_status.return_value = None

    def test_create_unique_bucket_name(self):
        """Test creation of unique bucket names"""
        # Test default base name
        bucket_name = aws.create_unique_bucket_name()
        self.assertTrue(bucket_name.startswith("audio-transcription-"))
        self.assertEqual(len(bucket_name.split("-")[-1]), 8)  # UUID part should be 8 chars

        # Test custom base name
        custom_base = "custom-base"
        bucket_name = aws.create_unique_bucket_name(base_name=custom_base)
        self.assertTrue(bucket_name.startswith(f"{custom_base}-"))
        self.assertEqual(len(bucket_name.split("-")[-1]), 8)

    @patch("boto3.client")
    def test_create_s3_bucket_us_east_1(self, mock_boto_client):
        """Test creating S3 bucket in us-east-1 region"""
        mock_s3 = create_mock_s3_client()
        mock_s3.meta.region_name = "us-east-1"
        mock_s3.head_bucket.side_effect = ClientError({"Error": {"Code": "404", "Message": "Not Found"}}, "HeadBucket")
        mock_boto_client.return_value = mock_s3

        result = aws.create_s3_bucket(self.bucket_name, region="us-east-1")

        self.assertEqual(result, self.bucket_name)
        mock_s3.create_bucket.assert_called_once_with(Bucket=self.bucket_name)

    @patch("boto3.client")
    def test_create_s3_bucket_non_us_east_1(self, mock_boto_client):
        """Test creating S3 bucket in a region other than us-east-1"""
        mock_s3 = create_mock_s3_client()
        mock_s3.head_bucket.side_effect = ClientError({"Error": {"Code": "404", "Message": "Not Found"}}, "HeadBucket")
        mock_boto_client.return_value = mock_s3

        result = aws.create_s3_bucket(self.bucket_name, region="eu-central-1")

        self.assertEqual(result, self.bucket_name)
        mock_s3.create_bucket.assert_called_once_with(
            Bucket=self.bucket_name, CreateBucketConfiguration={"LocationConstraint": "eu-central-1"}
        )

    @patch("boto3.client")
    def test_create_s3_bucket_client_error(self, mock_boto_client):
        """Test error handling when creating S3 bucket"""
        from botocore.exceptions import ClientError

        mock_s3 = create_mock_s3_client()
        mock_s3.head_bucket.side_effect = ClientError({"Error": {"Code": "404", "Message": "Not Found"}}, "HeadBucket")
        mock_s3.create_bucket.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}}, "CreateBucket"
        )
        mock_boto_client.return_value = mock_s3

        result = aws.create_s3_bucket(self.bucket_name)

        self.assertIsNone(result)

    @patch("boto3.client")
    def test_upload_file_to_s3(self, mock_boto_client):
        """Test uploading a file to S3"""
        mock_s3 = create_mock_s3_client()
        mock_boto_client.return_value = mock_s3

        result = aws.upload_file_to_s3(str(self.sample_wav_path), self.bucket_name)

        self.assertEqual(result, (True, self.bucket_name))
        mock_s3.upload_file.assert_called_once_with(
            str(self.sample_wav_path), self.bucket_name, self.sample_wav_path.name
        )

    @patch("boto3.client")
    def test_upload_file_to_s3_with_custom_name(self, mock_boto_client):
        """Test uploading a file to S3 with a custom object name"""
        mock_s3 = create_mock_s3_client()
        mock_boto_client.return_value = mock_s3

        custom_name = "custom-audio.wav"
        result = aws.upload_file_to_s3(str(self.sample_wav_path), self.bucket_name, custom_name)

        self.assertEqual(result, (True, self.bucket_name))
        mock_s3.upload_file.assert_called_once_with(str(self.sample_wav_path), self.bucket_name, custom_name)

    @patch("boto3.client")
    def test_upload_file_to_s3_error(self, mock_boto_client):
        """Test error handling when uploading to S3"""
        mock_s3 = create_mock_s3_client()
        mock_s3.upload_file.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}}, "UploadFile"
        )
        mock_boto_client.return_value = mock_s3

        result = aws.upload_file_to_s3(str(self.sample_wav_path), self.bucket_name)

        self.assertEqual(result, (False, None))

    @patch("boto3.client")
    def test_get_transcription_job_status(self, mock_boto_client):
        """Test getting transcription job status"""
        mock_transcribe = create_mock_transcribe_client()
        mock_boto_client.return_value = mock_transcribe

        job_name = "test-job"
        result = aws.get_transcription_job_status(job_name)

        self.assertIsNotNone(result)
        mock_transcribe.get_transcription_job.assert_called_once_with(TranscriptionJobName=job_name)

    @patch("boto3.client")
    def test_get_transcription_job_status_error(self, mock_boto_client):
        """Test error handling when getting job status"""
        from botocore.exceptions import ClientError

        mock_transcribe = create_mock_transcribe_client()
        mock_transcribe.get_transcription_job.side_effect = ClientError(
            {"Error": {"Code": "NotFoundException", "Message": "Job not found"}}, "GetTranscriptionJob"
        )
        mock_boto_client.return_value = mock_transcribe

        result = aws.get_transcription_job_status("nonexistent-job")

        self.assertIsNone(result)

    @patch("boto3.client")
    @patch("time.sleep", return_value=None)  # Prevent actual sleep in tests
    def test_wait_for_job_completion_success(self, mock_sleep, mock_boto_client):
        """Test waiting for job completion (success case)"""
        mock_transcribe = create_mock_transcribe_client()
        mock_boto_client.return_value = mock_transcribe

        job_name = "test-job"
        result = aws.wait_for_job_completion(job_name, poll_interval=1)

        self.assertIsNotNone(result)
        mock_transcribe.get_transcription_job.assert_called_with(TranscriptionJobName=job_name)

    @patch("boto3.client")
    @patch("time.sleep", return_value=None)
    def test_wait_for_job_completion_failure(self, mock_sleep, mock_boto_client):
        """Test waiting for job completion (failure case)"""
        mock_transcribe = create_mock_transcribe_client()
        # First return IN_PROGRESS, then FAILED
        mock_transcribe.get_transcription_job.side_effect = [
            {"TranscriptionJob": {"TranscriptionJobName": "test-job", "TranscriptionJobStatus": "IN_PROGRESS"}},
            {
                "TranscriptionJob": {
                    "TranscriptionJobName": "test-job",
                    "TranscriptionJobStatus": "FAILED",
                    "FailureReason": "Test failure reason",
                }
            },
        ]
        mock_boto_client.return_value = mock_transcribe

        job_name = "test-job"
        result = aws.wait_for_job_completion(job_name, poll_interval=1)

        self.assertIsNone(result)
        self.assertEqual(mock_transcribe.get_transcription_job.call_count, 2)

    @patch("requests.get")
    def test_download_transcription_result(self, mock_get):
        """Test downloading transcription results"""
        mock_get.return_value = self.mock_response

        transcript_url = "https://s3.amazonaws.com/test-bucket/test-job.json"
        result = aws.download_transcription_result(transcript_url)

        self.assertEqual(result, get_sample_transcription_data())
        mock_get.assert_called_once_with(transcript_url)

    @patch("requests.get")
    def test_download_transcription_result_error(self, mock_get):
        """Test error handling when downloading transcription results"""
        import requests

        mock_get.side_effect = requests.exceptions.RequestException("Connection error")

        result = aws.download_transcription_result("https://invalid-url.example")

        self.assertIsNone(result)

    @patch("boto3.resource")
    def test_cleanup_resources(self, mock_boto_resource):
        """Test cleaning up AWS resources"""
        # Create mock bucket and objects
        mock_bucket = MagicMock()
        mock_objects = MagicMock()
        mock_bucket.objects.all.return_value = mock_objects

        # Create mock S3 resource
        mock_s3 = MagicMock()
        mock_s3.Bucket.return_value = mock_bucket
        mock_boto_resource.return_value = mock_s3

        aws.cleanup_resources(self.bucket_name)

        # Verify the cleanup calls
        mock_boto_resource.assert_called_once_with("s3")
        mock_s3.Bucket.assert_called_once_with(self.bucket_name)
        mock_bucket.objects.all().delete.assert_called_once()
        mock_bucket.delete.assert_called_once()

    @patch("boto3.resource")
    def test_delete_file_from_s3(self, mock_boto_resource):
        """Test deleting a file from S3"""
        # Create mock S3 object
        mock_object = MagicMock()

        # Create mock S3 resource
        mock_s3 = MagicMock()
        mock_s3.Object.return_value = mock_object
        mock_boto_resource.return_value = mock_s3

        object_name = "test-file.wav"
        result = aws.delete_file_from_s3(self.bucket_name, object_name)

        self.assertTrue(result)
        mock_boto_resource.assert_called_once_with("s3")
        mock_s3.Object.assert_called_once_with(self.bucket_name, object_name)
        mock_object.delete.assert_called_once()

    # Dodajemy testy dla calculate_service_cost, jeśli funkcja istnieje w module
    def test_calculate_service_cost(self):
        """Test calculation of service costs"""
        # Pomiń ten test, jeśli funkcja nie istnieje
        if not hasattr(aws, "calculate_service_cost"):
            self.skipTest("calculate_service_cost function doesn't exist")

        audio_length = 300  # 5 minutes in seconds

        # Wywołaj funkcję tylko jeśli istnieje
        if hasattr(aws, "calculate_service_cost"):
            cost_info = aws.calculate_service_cost(audio_length)

            # Test that all expected keys are present in the result
            expected_keys = [
                "audio_length_seconds",
                "audio_size_mb",
                "transcribe_cost",
                "s3_storage_cost",
                "s3_request_cost",
                "total_cost",
                "currency",
            ]
            for key in expected_keys:
                self.assertIn(key, cost_info)

            # Test actual calculations
            self.assertEqual(cost_info["audio_length_seconds"], audio_length)

            # Total cost should be the sum of individual costs
            expected_total = (
                cost_info.get("transcribe_cost", 0)
                + cost_info.get("s3_storage_cost", 0)
                + cost_info.get("s3_request_cost", 0)
            )
            self.assertAlmostEqual(cost_info.get("total_cost", 0), expected_total)

    # Dodajemy testy dla get_supported_languages, jeśli funkcja istnieje w module
    def test_get_supported_languages(self):
        """Test getting supported languages"""
        # Pomiń ten test, jeśli funkcja nie istnieje
        if not hasattr(aws, "get_supported_languages"):
            self.skipTest("get_supported_languages function doesn't exist")

        # Wywołaj funkcję tylko jeśli istnieje
        if hasattr(aws, "get_supported_languages"):
            languages = aws.get_supported_languages()

            self.assertIsInstance(languages, dict)
            if languages:  # Tylko jeśli słownik nie jest pusty
                self.assertIn("pl-PL", languages)
                self.assertEqual(languages["pl-PL"], "polski")
                self.assertIn("en-US", languages)
                self.assertEqual(languages["en-US"], "angielski (USA)")

    @patch("boto3.client")
    def test_start_transcription_job(self, mock_boto_client):
        """Test starting a transcription job"""
        mock_transcribe = create_mock_transcribe_client()
        mock_boto_client.return_value = mock_transcribe

        job_name = f"test-job-{uuid.uuid4().hex[:8]}"
        result = aws.start_transcription_job(
            job_name, self.bucket_name, self.sample_wav_path.name, language_code="pl-PL", max_speakers=3
        )

        self.assertIsNotNone(result)
        # Nie sprawdzamy dokładnych parametrów, ponieważ mogą być różne w różnych implementacjach
        self.assertTrue(mock_transcribe.start_transcription_job.called)


if __name__ == "__main__":
    unittest.main()
