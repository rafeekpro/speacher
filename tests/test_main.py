#!/usr/bin/env python3
"""
Unit tests for the main module which handles the application workflow.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

# Import the module to test
from src.speecher import main

# Import test utilities
from tests.test_utils import create_sample_wav_file, get_sample_transcription_data, setup_test_data_dir


class TestMainModule(unittest.TestCase):
    """Test cases for main module functions"""

    def setUp(self):
        """Set up before each test"""
        self.test_data_dir = setup_test_data_dir()
        self.sample_wav_path = create_sample_wav_file()
        self.sample_transcription_data = get_sample_transcription_data()
        self.bucket_name = "test-bucket-12345678"
        self.job_name = "test-job-12345678"

    @patch("argparse.ArgumentParser.parse_args")
    def test_main_function_arguments(self, mock_parse_args):
        """Test main function argument parsing"""
        # Mock command line arguments
        mock_args = MagicMock()
        mock_args.audio_file = str(self.sample_wav_path)
        mock_args.keep_resources = False
        mock_args.region = "eu-central-1"
        mock_args.bucket_name = None
        mock_args.language = "pl-PL"
        mock_args.max_speakers = 5
        mock_args.output_file = None
        mock_args.include_timestamps = True
        mock_args.no_timestamps = False
        mock_args.audio_length = None
        mock_args.show_cost = False
        mock_parse_args.return_value = mock_args

        # Mock AWS functions to avoid actual API calls
        with (
            patch("src.speecher.aws.create_unique_bucket_name") as mock_create_bucket_name,
            patch("src.speecher.aws.create_s3_bucket") as mock_create_bucket,
            patch("src.speecher.aws.upload_file_to_s3") as mock_upload_file,
            patch("src.speecher.aws.start_transcription_job") as mock_start_job,
            patch("src.speecher.aws.wait_for_job_completion") as mock_wait_for_job,
            patch("src.speecher.aws.download_transcription_result") as mock_download_result,
            patch("src.speecher.transcription.process_transcription_result") as mock_process_result,
            patch("src.speecher.aws.cleanup_resources") as mock_cleanup,
            patch("src.speecher.aws.get_supported_languages") as mock_get_languages,
        ):
            # Setup return values for the mocks
            mock_create_bucket_name.return_value = self.bucket_name
            mock_create_bucket.return_value = True
            mock_upload_file.return_value = True
            mock_start_job.return_value = {"TranscriptionJob": {"TranscriptionJobName": self.job_name}}

            mock_job_info = {
                "TranscriptionJob": {
                    "TranscriptionJobName": self.job_name,
                    "TranscriptionJobStatus": "COMPLETED",
                    "Transcript": {"TranscriptFileUri": "https://s3.amazonaws.com/test-bucket/test-job.json"},
                }
            }
            mock_wait_for_job.return_value = mock_job_info
            mock_download_result.return_value = self.sample_transcription_data
            mock_process_result.return_value = True
            mock_get_languages.return_value = {"pl-PL": "polski", "en-US": "angielski (USA)"}

            # Call the main function
            with patch("builtins.open", mock_open(read_data=b"dummy_wav_data")):
                result = main.main()

                # Verify that the main function completed successfully
                self.assertEqual(result, 0)

                # Verify that all the workflow steps were called
                mock_create_bucket_name.assert_called_once()
                mock_create_bucket.assert_called_once_with(self.bucket_name, region="eu-central-1")
                mock_upload_file.assert_called_once()
                mock_start_job.assert_called_once()
                mock_wait_for_job.assert_called_once()
                mock_download_result.assert_called_once()
                mock_process_result.assert_called_once_with(
                    self.sample_transcription_data, output_file=None, include_timestamps=True
                )
                mock_cleanup.assert_called_once_with(self.bucket_name)

    @patch("argparse.ArgumentParser.parse_args")
    def test_main_function_with_existing_bucket(self, mock_parse_args):
        """Test main function with an existing bucket"""
        # Mock command line arguments
        mock_args = MagicMock()
        mock_args.audio_file = str(self.sample_wav_path)
        mock_args.keep_resources = False
        mock_args.region = None
        mock_args.bucket_name = "existing-bucket"  # Use an existing bucket
        mock_args.language = "pl-PL"
        mock_args.max_speakers = 5
        mock_args.output_file = None
        mock_args.include_timestamps = True
        mock_args.no_timestamps = False
        mock_args.audio_length = None
        mock_args.show_cost = False
        mock_parse_args.return_value = mock_args

        # Mock AWS functions
        with (
            patch("src.speecher.aws.create_s3_bucket") as mock_create_bucket,
            patch("src.speecher.aws.upload_file_to_s3") as mock_upload_file,
            patch("src.speecher.aws.start_transcription_job") as mock_start_job,
            patch("src.speecher.aws.wait_for_job_completion") as mock_wait_for_job,
            patch("src.speecher.aws.download_transcription_result") as mock_download_result,
            patch("src.speecher.transcription.process_transcription_result") as mock_process_result,
            patch("src.speecher.aws.delete_file_from_s3") as mock_delete_file,
            patch("src.speecher.aws.get_supported_languages") as mock_get_languages,
        ):
            # Setup return values for the mocks
            mock_upload_file.return_value = True
            mock_start_job.return_value = {"TranscriptionJob": {"TranscriptionJobName": self.job_name}}

            mock_job_info = {
                "TranscriptionJob": {
                    "TranscriptionJobName": self.job_name,
                    "TranscriptionJobStatus": "COMPLETED",
                    "Transcript": {"TranscriptFileUri": "https://s3.amazonaws.com/test-bucket/test-job.json"},
                }
            }
            mock_wait_for_job.return_value = mock_job_info
            mock_download_result.return_value = self.sample_transcription_data
            mock_process_result.return_value = True
            mock_delete_file.return_value = True
            mock_get_languages.return_value = {"pl-PL": "polski", "en-US": "angielski (USA)"}

            # Call the main function
            with patch("builtins.open", mock_open(read_data=b"dummy_wav_data")):
                result = main.main()

                # Verify that the main function completed successfully
                self.assertEqual(result, 0)

                # Verify that the existing bucket was used
                mock_create_bucket.assert_not_called()
                mock_upload_file.assert_called_once_with(
                    str(self.sample_wav_path), "existing-bucket", os.path.basename(str(self.sample_wav_path))
                )

                # Verify that only the file was deleted, not the bucket
                mock_delete_file.assert_called_once()

    @patch("argparse.ArgumentParser.parse_args")
    def test_main_function_keep_resources(self, mock_parse_args):
        """Test main function with keep_resources flag"""
        # Mock command line arguments
        mock_args = MagicMock()
        mock_args.audio_file = str(self.sample_wav_path)
        mock_args.keep_resources = True  # Keep resources after completion
        mock_args.region = None
        mock_args.bucket_name = None
        mock_args.language = "pl-PL"
        mock_args.max_speakers = 5
        mock_args.output_file = None
        mock_args.include_timestamps = True
        mock_args.no_timestamps = False
        mock_args.audio_length = None
        mock_args.show_cost = False
        mock_parse_args.return_value = mock_args

        # Mock AWS functions
        with (
            patch("src.speecher.aws.create_unique_bucket_name") as mock_create_bucket_name,
            patch("src.speecher.aws.create_s3_bucket") as mock_create_bucket,
            patch("src.speecher.aws.upload_file_to_s3") as mock_upload_file,
            patch("src.speecher.aws.start_transcription_job") as mock_start_job,
            patch("src.speecher.aws.wait_for_job_completion") as mock_wait_for_job,
            patch("src.speecher.aws.download_transcription_result") as mock_download_result,
            patch("src.speecher.transcription.process_transcription_result") as mock_process_result,
            patch("src.speecher.aws.cleanup_resources") as mock_cleanup,
            patch("src.speecher.aws.get_supported_languages") as mock_get_languages,
            patch("logging.Logger.info") as mock_logger_info,
        ):
            # Setup return values for the mocks
            mock_create_bucket_name.return_value = self.bucket_name
            mock_create_bucket.return_value = True
            mock_upload_file.return_value = True
            mock_start_job.return_value = {"TranscriptionJob": {"TranscriptionJobName": self.job_name}}

            mock_job_info = {
                "TranscriptionJob": {
                    "TranscriptionJobName": self.job_name,
                    "TranscriptionJobStatus": "COMPLETED",
                    "Transcript": {"TranscriptFileUri": "https://s3.amazonaws.com/test-bucket/test-job.json"},
                }
            }
            mock_wait_for_job.return_value = mock_job_info
            mock_download_result.return_value = self.sample_transcription_data
            mock_process_result.return_value = True
            mock_get_languages.return_value = {"pl-PL": "polski", "en-US": "angielski (USA)"}

            # Call the main function
            with patch("builtins.open", mock_open(read_data=b"dummy_wav_data")):
                result = main.main()

                # Verify that the main function completed successfully
                self.assertEqual(result, 0)

                # Verify that resources were not cleaned up
                mock_cleanup.assert_not_called()

                # Check that the message about kept resources was logged
                # Since job_name is generated with UUID, we need to check for partial match
                kept_resources_logged = False
                for call in mock_logger_info.call_args_list:
                    if len(call[0]) > 0:
                        message = str(call[0][0])
                        if "Zasoby nie zostały usunięte" in message and self.bucket_name in message:
                            kept_resources_logged = True
                            break

                self.assertTrue(kept_resources_logged, "Expected log message about kept resources not found")

    @patch("argparse.ArgumentParser.parse_args")
    def test_main_function_with_timestamps(self, mock_parse_args):
        """Test main function with and without timestamps"""
        # Test no_timestamps=True which should disable timestamps
        mock_args = MagicMock()
        mock_args.audio_file = str(self.sample_wav_path)
        mock_args.keep_resources = False
        mock_args.region = None
        mock_args.bucket_name = None
        mock_args.language = "pl-PL"
        mock_args.max_speakers = 5
        mock_args.output_file = None
        mock_args.include_timestamps = True
        mock_args.no_timestamps = True  # This should override include_timestamps
        mock_args.audio_length = None
        mock_args.show_cost = False
        mock_parse_args.return_value = mock_args

        # Mock AWS functions
        with (
            patch("src.speecher.aws.create_unique_bucket_name") as mock_create_bucket_name,
            patch("src.speecher.aws.create_s3_bucket") as mock_create_bucket,
            patch("src.speecher.aws.upload_file_to_s3") as mock_upload_file,
            patch("src.speecher.aws.start_transcription_job") as mock_start_job,
            patch("src.speecher.aws.wait_for_job_completion") as mock_wait_for_job,
            patch("src.speecher.aws.download_transcription_result") as mock_download_result,
            patch("src.speecher.transcription.process_transcription_result") as mock_process_result,
            patch("src.speecher.aws.cleanup_resources") as mock_cleanup,
            patch("src.speecher.aws.get_supported_languages") as mock_get_languages,
        ):
            # Setup return values for the mocks
            mock_create_bucket_name.return_value = self.bucket_name
            mock_create_bucket.return_value = True
            mock_upload_file.return_value = True
            mock_start_job.return_value = {"TranscriptionJob": {"TranscriptionJobName": self.job_name}}

            mock_job_info = {
                "TranscriptionJob": {
                    "TranscriptionJobName": self.job_name,
                    "TranscriptionJobStatus": "COMPLETED",
                    "Transcript": {"TranscriptFileUri": "https://s3.amazonaws.com/test-bucket/test-job.json"},
                }
            }
            mock_wait_for_job.return_value = mock_job_info
            mock_download_result.return_value = self.sample_transcription_data
            mock_process_result.return_value = True
            mock_get_languages.return_value = {"pl-PL": "polski", "en-US": "angielski (USA)"}

            # Call the main function
            with patch("builtins.open", mock_open(read_data=b"dummy_wav_data")):
                result = main.main()

                # Verify that the main function completed successfully
                self.assertEqual(result, 0)

                # Verify that process_transcription_result was called with include_timestamps=False
                mock_process_result.assert_called_once_with(
                    self.sample_transcription_data, output_file=None, include_timestamps=False
                )

    @patch("argparse.ArgumentParser.parse_args")
    def test_main_function_with_output_file(self, mock_parse_args):
        """Test main function with output file specified"""
        # Create temporary file for output
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            output_path = temp_file.name

        try:
            # Mock command line arguments
            mock_args = MagicMock()
            mock_args.audio_file = str(self.sample_wav_path)
            mock_args.keep_resources = False
            mock_args.region = None
            mock_args.bucket_name = None
            mock_args.language = "pl-PL"
            mock_args.max_speakers = 5
            mock_args.output_file = output_path  # Specify output file
            mock_args.include_timestamps = True
            mock_args.no_timestamps = False
            mock_args.audio_length = None
            mock_args.show_cost = False
            mock_parse_args.return_value = mock_args

            # Mock AWS functions
            with (
                patch("src.speecher.aws.create_unique_bucket_name") as mock_create_bucket_name,
                patch("src.speecher.aws.create_s3_bucket") as mock_create_bucket,
                patch("src.speecher.aws.upload_file_to_s3") as mock_upload_file,
                patch("src.speecher.aws.start_transcription_job") as mock_start_job,
                patch("src.speecher.aws.wait_for_job_completion") as mock_wait_for_job,
                patch("src.speecher.aws.download_transcription_result") as mock_download_result,
                patch("src.speecher.transcription.process_transcription_result") as mock_process_result,
                patch("src.speecher.aws.cleanup_resources") as mock_cleanup,
                patch("src.speecher.aws.get_supported_languages") as mock_get_languages,
            ):
                # Setup return values for the mocks
                mock_create_bucket_name.return_value = self.bucket_name
                mock_create_bucket.return_value = True
                mock_upload_file.return_value = True
                mock_start_job.return_value = {"TranscriptionJob": {"TranscriptionJobName": self.job_name}}

                mock_job_info = {
                    "TranscriptionJob": {
                        "TranscriptionJobName": self.job_name,
                        "TranscriptionJobStatus": "COMPLETED",
                        "Transcript": {"TranscriptFileUri": "https://s3.amazonaws.com/test-bucket/test-job.json"},
                    }
                }
                mock_wait_for_job.return_value = mock_job_info
                mock_download_result.return_value = self.sample_transcription_data
                mock_process_result.return_value = True
                mock_get_languages.return_value = {"pl-PL": "polski", "en-US": "angielski (USA)"}

                # Call the main function
                with patch("builtins.open", mock_open(read_data=b"dummy_wav_data")):
                    result = main.main()

                    # Verify that the main function completed successfully
                    self.assertEqual(result, 0)

                    # Verify that process_transcription_result was called with the correct output file
                    mock_process_result.assert_called_once_with(
                        self.sample_transcription_data, output_file=output_path, include_timestamps=True
                    )
        finally:
            # Clean up temp file
            Path(output_path).unlink(missing_ok=True)

    @patch("argparse.ArgumentParser.parse_args")
    def test_main_function_missing_audio_file(self, mock_parse_args):
        """Test main function when audio file doesn't exist"""
        # Mock command line arguments with a nonexistent file
        mock_args = MagicMock()
        mock_args.audio_file = "/tmp/nonexistent-file.wav"
        mock_args.keep_resources = False
        mock_args.region = None
        mock_args.bucket_name = None
        mock_args.language = "pl-PL"
        mock_args.max_speakers = 5
        mock_args.output_file = None
        mock_args.include_timestamps = True
        mock_args.no_timestamps = False
        mock_args.audio_length = None
        mock_args.show_cost = False
        mock_parse_args.return_value = mock_args

        # Mock AWS functions
        with (
            patch("src.speecher.aws.get_supported_languages") as mock_get_languages,
            patch("logging.Logger.error") as mock_logger_error,
        ):
            mock_get_languages.return_value = {"pl-PL": "polski", "en-US": "angielski (USA)"}

            # Call the main function
            result = main.main()

            # Verify that the main function returned an error
            self.assertEqual(result, 1)

            # Verify that an error was logged
            mock_logger_error.assert_any_call(f"Plik {'/tmp/nonexistent-file.wav'} nie istnieje")

    @patch("argparse.ArgumentParser.parse_args")
    def test_main_function_non_wav_file(self, mock_parse_args):
        """Test main function when file is not a WAV file"""
        # Create a temporary file that's not a WAV file
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temp_file:
            temp_file.write(b"This is not a WAV file")
            non_wav_path = temp_file.name

        try:
            # Mock command line arguments
            mock_args = MagicMock()
            mock_args.audio_file = non_wav_path
            mock_args.keep_resources = False
            mock_args.region = None
            mock_args.bucket_name = None
            mock_args.language = "pl-PL"
            mock_args.max_speakers = 5
            mock_args.output_file = None
            mock_args.include_timestamps = True
            mock_args.no_timestamps = False
            mock_args.audio_length = None
            mock_args.show_cost = False
            mock_parse_args.return_value = mock_args

            # Mock AWS functions
            with (
                patch("src.speecher.aws.get_supported_languages") as mock_get_languages,
                patch("logging.Logger.error") as mock_logger_error,
            ):
                mock_get_languages.return_value = {"pl-PL": "polski", "en-US": "angielski (USA)"}

                # Call the main function
                result = main.main()

                # Verify that the main function returned an error
                self.assertEqual(result, 1)

                # Verify that an error was logged
                mock_logger_error.assert_any_call(f"Plik {non_wav_path} nie jest plikiem .wav")
        finally:
            # Clean up temp file
            Path(non_wav_path).unlink(missing_ok=True)

    @patch("argparse.ArgumentParser.parse_args")
    def test_main_function_show_cost(self, mock_parse_args):
        """Test main function with show_cost flag"""
        # Mock command line arguments
        mock_args = MagicMock()
        mock_args.audio_file = str(self.sample_wav_path)
        mock_args.keep_resources = False
        mock_args.region = None
        mock_args.bucket_name = None
        mock_args.language = "pl-PL"
        mock_args.max_speakers = 5
        mock_args.output_file = None
        mock_args.include_timestamps = True
        mock_args.no_timestamps = False
        mock_args.audio_length = 300.0  # 5 minutes
        mock_args.show_cost = True
        mock_parse_args.return_value = mock_args

        # Mock AWS functions
        with (
            patch("src.speecher.aws.create_unique_bucket_name") as mock_create_bucket_name,
            patch("src.speecher.aws.create_s3_bucket") as mock_create_bucket,
            patch("src.speecher.aws.upload_file_to_s3") as mock_upload_file,
            patch("src.speecher.aws.start_transcription_job") as mock_start_job,
            patch("src.speecher.aws.wait_for_job_completion") as mock_wait_for_job,
            patch("src.speecher.aws.download_transcription_result") as mock_download_result,
            patch("src.speecher.transcription.process_transcription_result") as mock_process_result,
            patch("src.speecher.aws.cleanup_resources") as mock_cleanup,
            patch("src.speecher.aws.calculate_service_cost") as mock_calculate_cost,
            patch("src.speecher.aws.get_supported_languages") as mock_get_languages,
            patch("builtins.print") as mock_print,
        ):
            # Setup return values for the mocks
            mock_create_bucket_name.return_value = self.bucket_name
            mock_create_bucket.return_value = True
            mock_upload_file.return_value = True
            mock_start_job.return_value = {"TranscriptionJob": {"TranscriptionJobName": self.job_name}}

            mock_job_info = {
                "TranscriptionJob": {
                    "TranscriptionJobName": self.job_name,
                    "TranscriptionJobStatus": "COMPLETED",
                    "Transcript": {"TranscriptFileUri": "https://s3.amazonaws.com/test-bucket/test-job.json"},
                }
            }
            mock_wait_for_job.return_value = mock_job_info
            mock_download_result.return_value = self.sample_transcription_data
            mock_process_result.return_value = True

            cost_info = {
                "audio_length_seconds": 300.0,
                "audio_size_mb": 50.0,
                "transcribe_cost": 0.12,
                "s3_storage_cost": 0.000035,
                "s3_request_cost": 0.000050,
                "total_cost": 0.120085,
                "currency": "USD",
            }
            mock_calculate_cost.return_value = cost_info
            mock_get_languages.return_value = {"pl-PL": "polski", "en-US": "angielski (USA)"}

            # Call the main function
            with patch("builtins.open", mock_open(read_data=b"dummy_wav_data")):
                result = main.main()

                # Verify that the main function completed successfully
                self.assertEqual(result, 0)

                # Verify that calculate_service_cost was called
                mock_calculate_cost.assert_called_once_with(300.0, "pl-PL")

                # Verify that cost information was printed
                mock_print.assert_any_call("\n=== INFORMACJE O KOSZTACH TRANSKRYPCJI ===\n")

    @patch("argparse.ArgumentParser.parse_args")
    def test_main_function_aws_failure(self, mock_parse_args):
        """Test main function when AWS operations fail"""
        # Mock command line arguments
        mock_args = MagicMock()
        mock_args.audio_file = str(self.sample_wav_path)
        mock_args.keep_resources = False
        mock_args.region = None
        mock_args.bucket_name = None
        mock_args.language = "pl-PL"
        mock_args.max_speakers = 5
        mock_args.output_file = None
        mock_args.include_timestamps = True
        mock_args.no_timestamps = False
        mock_args.audio_length = None
        mock_args.show_cost = False
        mock_parse_args.return_value = mock_args

        # Test scenarios where different AWS operations fail

        # Scenario 1: S3 bucket creation fails
        with (
            patch("src.speecher.aws.create_unique_bucket_name") as mock_create_bucket_name,
            patch("src.speecher.aws.create_s3_bucket") as mock_create_bucket,
            patch("src.speecher.aws.get_supported_languages") as mock_get_languages,
        ):
            mock_create_bucket_name.return_value = self.bucket_name
            mock_create_bucket.return_value = False  # Bucket creation fails
            mock_get_languages.return_value = {"pl-PL": "polski", "en-US": "angielski (USA)"}

            # Call the main function
            with patch("builtins.open", mock_open(read_data=b"dummy_wav_data")):
                result = main.main()

                # Verify that the main function returned an error
                self.assertEqual(result, 1)

        # Scenario 2: File upload fails
        with (
            patch("src.speecher.aws.create_unique_bucket_name") as mock_create_bucket_name,
            patch("src.speecher.aws.create_s3_bucket") as mock_create_bucket,
            patch("src.speecher.aws.upload_file_to_s3") as mock_upload_file,
            patch("src.speecher.aws.get_supported_languages") as mock_get_languages,
        ):
            mock_create_bucket_name.return_value = self.bucket_name
            mock_create_bucket.return_value = True
            mock_upload_file.return_value = False  # Upload fails
            mock_get_languages.return_value = {"pl-PL": "polski", "en-US": "angielski (USA)"}

            # Call the main function
            with patch("builtins.open", mock_open(read_data=b"dummy_wav_data")):
                result = main.main()

                # Verify that the main function returned an error
                self.assertEqual(result, 1)


if __name__ == "__main__":
    unittest.main()
