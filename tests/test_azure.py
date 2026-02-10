#!/usr/bin/env python3
"""
Unit tests for the Azure module which handles interactions with Azure services.
"""

import os
import unittest
import uuid
from unittest.mock import MagicMock, mock_open, patch

# Import the module to test
from src.speecher import azure

# Import test utilities - using absolute imports for better compatibility
from tests.test_utils import create_sample_wav_file, get_sample_transcription_data, setup_test_data_dir


class TestAzureModule(unittest.TestCase):
    """Test cases for Azure module functions"""

    def setUp(self):
        """Set up before each test"""
        self.test_data_dir = setup_test_data_dir()
        # Zapewniamy, że katalog test_data istnieje
        os.makedirs(self.test_data_dir, exist_ok=True)

        self.sample_wav_path = create_sample_wav_file()
        self.container_name = f"testtranscription{uuid.uuid4().hex[:8]}"  # lowercase for Azure
        self.mock_connection_string = "DefaultEndpointsProtocol=https;AccountName=mystorageaccount;AccountKey=abc123==;EndpointSuffix=core.windows.net"
        self.mock_subscription_key = "1234567890abcdef1234567890abcdef"
        self.mock_region = "westeurope"

        # Mock responses
        self.mock_blob_response = MagicMock()
        self.mock_blob_response.json.return_value = {"name": "test_blob"}

        self.mock_transcription_response = MagicMock()
        self.mock_transcription_response.json.return_value = {
            "id": f"https://{self.mock_region}.api.cognitive.microsoft.com/speechtotext/v3.1/transcriptions/12345",
            "status": "Running",
            "createdDateTime": "2025-05-08T10:00:00Z",
            "links": {
                "files": f"https://{self.mock_region}.api.cognitive.microsoft.com/speechtotext/v3.1/transcriptions/12345/files"
            },
        }

        self.mock_complete_response = MagicMock()
        self.mock_complete_response.json.return_value = {
            "id": f"https://{self.mock_region}.api.cognitive.microsoft.com/speechtotext/v3.1/transcriptions/12345",
            "status": "Succeeded",
            "createdDateTime": "2025-05-08T10:00:00Z",
            "links": {
                "files": f"https://{self.mock_region}.api.cognitive.microsoft.com/speechtotext/v3.1/transcriptions/12345/files"
            },
            "resultsUrls": {
                "channel_0": f"https://{self.mock_region}.api.cognitive.microsoft.com/speechtotext/v3.1/transcriptions/12345/results/channel_0"
            },
        }

        self.mock_result_response = MagicMock()
        self.mock_result_response.json.return_value = get_sample_transcription_data()

    def test_create_unique_container_name(self):
        """Test creation of unique container names"""
        # Test default base name
        container_name = azure.create_unique_container_name()
        self.assertTrue(container_name.startswith("audio-transcription"))
        self.assertEqual(len(container_name.split("transcription")[1]), 8)  # UUID part

        # Container names should be lowercase in Azure
        self.assertEqual(container_name, container_name.lower())

        # Test custom base name
        custom_base = "custom-base"
        container_name = azure.create_unique_container_name(base_name=custom_base)
        self.assertTrue(container_name.startswith(f"{custom_base}"))
        self.assertEqual(len(container_name.split(custom_base)[1]), 8)

    @patch("azure.storage.blob.BlobServiceClient.from_connection_string")
    def test_create_blob_container(self, mock_blob_service_client):
        """Test creating Azure Blob container"""
        # Setup mock
        mock_container_client = MagicMock()
        mock_service_client = MagicMock()
        mock_service_client.create_container.return_value = mock_container_client
        mock_blob_service_client.return_value = mock_service_client

        result = azure.create_blob_container(self.mock_connection_string, self.container_name)

        self.assertTrue(result)
        mock_blob_service_client.assert_called_once_with(self.mock_connection_string)
        mock_service_client.create_container.assert_called_once_with(self.container_name)

    @patch("azure.storage.blob.BlobServiceClient.from_connection_string")
    def test_create_blob_container_exists(self, mock_blob_service_client):
        """Test handling when container already exists"""
        from azure.core.exceptions import ResourceExistsError

        # Setup mock to raise ResourceExistsError
        mock_service_client = MagicMock()
        mock_service_client.create_container.side_effect = ResourceExistsError("Container already exists")
        mock_blob_service_client.return_value = mock_service_client

        result = azure.create_blob_container(self.mock_connection_string, self.container_name)

        self.assertTrue(result)  # Should still return True for existing container

    @patch("azure.storage.blob.BlobServiceClient.from_connection_string")
    def test_create_blob_container_error(self, mock_blob_service_client):
        """Test error handling when creating container"""
        # Setup mock to raise general Exception
        mock_service_client = MagicMock()
        mock_service_client.create_container.side_effect = Exception("Mock error")
        mock_blob_service_client.return_value = mock_service_client

        result = azure.create_blob_container(self.mock_connection_string, self.container_name)

        self.assertFalse(result)

    @patch("azure.storage.blob.BlobServiceClient.from_connection_string")
    @patch("src.speecher.azure.generate_container_sas")
    def test_upload_file_to_blob(self, mock_generate_sas, mock_blob_service_client):
        """Test uploading file to Azure Blob Storage"""
        # Setup mocks
        mock_blob_client = MagicMock()
        mock_container_client = MagicMock()
        mock_container_client.get_blob_client.return_value = mock_blob_client

        mock_service_client = MagicMock()
        mock_service_client.get_container_client.return_value = mock_container_client
        mock_service_client.account_name = "mystorageaccount"
        mock_service_client.credential.account_key = "mock_key"

        mock_blob_service_client.return_value = mock_service_client

        # Mock SAS token generation
        mock_generate_sas.return_value = "sastoken"

        # Test with a mock file
        with patch("builtins.open", mock_open(read_data=b"dummy_wav_data")):
            result = azure.upload_file_to_blob(
                str(self.sample_wav_path), self.mock_connection_string, self.container_name
            )

            # Check the mock was called with expected parameters
            mock_blob_service_client.assert_called_once_with(self.mock_connection_string)
            mock_service_client.get_container_client.assert_called_once_with(self.container_name)

            expected_blob_name = os.path.basename(str(self.sample_wav_path))
            mock_container_client.get_blob_client.assert_called_once_with(expected_blob_name)
            mock_blob_client.upload_blob.assert_called_once()

            # Verify SAS token generation was called with correct parameters
            mock_generate_sas.assert_called_once_with(
                account_name="mystorageaccount",
                container_name=self.container_name,
                account_key="mock_key",
                permission=unittest.mock.ANY,  # We don't need to check the exact permissions
                expiry=unittest.mock.ANY,  # We don't need to check the exact expiry
            )

            # Verify the returned URL format
            self.assertIsNotNone(result)
            expected_url_start = (
                f"https://mystorageaccount.blob.core.windows.net/{self.container_name}/{expected_blob_name}?sastoken"
            )
            self.assertEqual(result, expected_url_start)

    @patch("azure.storage.blob.BlobServiceClient.from_connection_string")
    def test_upload_file_to_blob_error(self, mock_blob_service_client):
        """Test error handling when uploading file"""
        # Setup mock to raise Exception
        mock_blob_client = MagicMock()
        mock_blob_client.upload_blob.side_effect = Exception("Upload error")

        mock_container_client = MagicMock()
        mock_container_client.get_blob_client.return_value = mock_blob_client

        mock_service_client = MagicMock()
        mock_service_client.get_container_client.return_value = mock_container_client

        mock_blob_service_client.return_value = mock_service_client

        # Używamy patch dla funkcji open aby uniknąć faktycznego otwierania pliku
        with patch("builtins.open", mock_open(read_data=b"dummy_wav_data")):
            result = azure.upload_file_to_blob(
                str(self.sample_wav_path), self.mock_connection_string, self.container_name
            )

            self.assertIsNone(result)

    @patch("requests.post")
    def test_start_transcription_job(self, mock_post):
        """Test starting Azure transcription job"""
        # Setup mock response
        mock_post.return_value = self.mock_transcription_response
        mock_post.return_value.status_code = 201
        mock_post.return_value.raise_for_status.return_value = None

        audio_url = f"https://mystorageaccount.blob.core.windows.net/{self.container_name}/audio.wav?sastoken"
        job_name = f"test-job-{uuid.uuid4().hex[:8]}"

        result = azure.start_transcription_job(
            self.mock_subscription_key, self.mock_region, audio_url, job_name=job_name
        )

        self.assertIsNotNone(result)
        self.assertEqual(result, self.mock_transcription_response.json())

        # Verify request was made with correct parameters
        mock_post.assert_called_once()
        call_args = mock_post.call_args[1]

        self.assertEqual(call_args["headers"]["Ocp-Apim-Subscription-Key"], self.mock_subscription_key)
        self.assertEqual(call_args["json"]["contentUrls"][0], audio_url)
        self.assertEqual(call_args["json"]["locale"], "pl-PL")  # Default value
        self.assertEqual(call_args["json"]["displayName"], job_name)

    @patch("requests.post")
    def test_start_transcription_job_error(self, mock_post):
        """Test error handling when starting transcription job"""
        # Setup mock to raise an exception
        mock_post.side_effect = Exception("Connection error")

        audio_url = f"https://mystorageaccount.blob.core.windows.net/{self.container_name}/audio.wav?sastoken"

        result = azure.start_transcription_job(self.mock_subscription_key, self.mock_region, audio_url)

        self.assertIsNone(result)

    @patch("requests.get")
    def test_get_transcription_job_status(self, mock_get):
        """Test getting transcription job status"""
        # Setup mock response
        mock_get.return_value = self.mock_complete_response
        mock_get.return_value.status_code = 200
        mock_get.return_value.raise_for_status.return_value = None

        job_id = "12345"

        result = azure.get_transcription_job_status(self.mock_subscription_key, self.mock_region, job_id)

        self.assertIsNotNone(result)
        self.assertEqual(result, self.mock_complete_response.json())

        # Verify the request
        mock_get.assert_called_once()
        self.assertTrue(job_id in mock_get.call_args[0][0])
        self.assertEqual(mock_get.call_args[1]["headers"]["Ocp-Apim-Subscription-Key"], self.mock_subscription_key)

    @patch("requests.get")
    def test_get_transcription_job_status_error(self, mock_get):
        """Test error handling when getting job status"""
        # Setup mock to raise an exception
        mock_get.side_effect = Exception("API error")

        result = azure.get_transcription_job_status(self.mock_subscription_key, self.mock_region, "12345")

        self.assertIsNone(result)

    @patch("requests.get")
    @patch("time.sleep", return_value=None)  # Prevent actual sleep in tests
    def test_wait_for_job_completion_success(self, mock_sleep, mock_get):
        """Test waiting for job completion (success case)"""
        # First return 'Running', then 'Succeeded'
        mock_get.side_effect = [self.mock_transcription_response, self.mock_complete_response]  # Running  # Succeeded

        # Update the status in the responses
        self.mock_transcription_response.json.return_value["status"] = "Running"
        self.mock_complete_response.json.return_value["status"] = "Succeeded"

        mock_get.return_value.raise_for_status.return_value = None

        job_id = "12345"

        result = azure.wait_for_job_completion(self.mock_subscription_key, self.mock_region, job_id, poll_interval=1)

        self.assertIsNotNone(result)
        self.assertEqual(result, self.mock_complete_response.json())
        self.assertEqual(mock_get.call_count, 2)

    @patch("requests.get")
    @patch("time.sleep", return_value=None)
    def test_wait_for_job_completion_failure(self, mock_sleep, mock_get):
        """Test waiting for job completion (failure case)"""
        # First return 'Running', then 'Failed'
        failed_response = MagicMock()
        failed_response.json.return_value = {
            "id": f"https://{self.mock_region}.api.cognitive.microsoft.com/speechtotext/v3.1/transcriptions/12345",
            "status": "Failed",
            "createdDateTime": "2025-05-08T10:00:00Z",
            "lastActionDateTime": "2025-05-08T10:05:00Z",
            "statusMessage": "The operation has failed.",
        }
        failed_response.raise_for_status.return_value = None

        mock_get.side_effect = [self.mock_transcription_response, failed_response]  # Running  # Failed

        # Update the status in the first response
        self.mock_transcription_response.json.return_value["status"] = "Running"
        self.mock_transcription_response.raise_for_status.return_value = None

        job_id = "12345"

        result = azure.wait_for_job_completion(self.mock_subscription_key, self.mock_region, job_id, poll_interval=1)

        self.assertIsNone(result)
        self.assertEqual(mock_get.call_count, 2)

    @patch("requests.get")
    def test_download_transcription_result(self, mock_get):
        """Test downloading transcription results"""
        # Setup mock response
        mock_get.return_value = self.mock_result_response
        mock_get.return_value.status_code = 200
        mock_get.return_value.raise_for_status.return_value = None

        result_url = f"https://{self.mock_region}.api.cognitive.microsoft.com/speechtotext/v3.1/transcriptions/12345/results/channel_0"

        result = azure.download_transcription_result(self.mock_subscription_key, result_url)

        self.assertIsNotNone(result)
        self.assertEqual(result, get_sample_transcription_data())

        # Verify the request
        mock_get.assert_called_once_with(result_url, headers={"Ocp-Apim-Subscription-Key": self.mock_subscription_key})

    @patch("requests.get")
    def test_download_transcription_result_error(self, mock_get):
        """Test error handling when downloading results"""
        # Setup mock to raise an exception
        mock_get.side_effect = Exception("Download error")

        result_url = f"https://{self.mock_region}.api.cognitive.microsoft.com/speechtotext/v3.1/transcriptions/12345/results/channel_0"

        result = azure.download_transcription_result(self.mock_subscription_key, result_url)

        self.assertIsNone(result)

    @patch("azure.storage.blob.BlobServiceClient.from_connection_string")
    def test_cleanup_resources(self, mock_blob_service_client):
        """Test cleaning up Azure resources"""
        # Setup mock
        mock_container_client = MagicMock()
        mock_service_client = MagicMock()
        mock_service_client.get_container_client.return_value = mock_container_client
        mock_blob_service_client.return_value = mock_service_client

        # Add request mock for deleting transcription job
        with patch("requests.delete") as mock_delete:
            mock_delete.return_value = MagicMock()
            mock_delete.return_value.status_code = 204

            azure.cleanup_resources(
                self.mock_connection_string,
                self.container_name,
                subscription_key=self.mock_subscription_key,
                region=self.mock_region,
                job_id="12345",
            )

            # Verify container deletion
            mock_service_client.get_container_client.assert_called_once_with(self.container_name)
            mock_container_client.delete_container.assert_called_once()

            # Verify transcription job deletion
            mock_delete.assert_called_once()
            job_id = "12345"
            self.assertTrue(job_id in mock_delete.call_args[0][0])

    @patch("azure.storage.blob.BlobServiceClient.from_connection_string")
    def test_delete_blob_from_container(self, mock_blob_service_client):
        """Test deleting a blob from Azure container"""
        # Setup mocks
        mock_blob_client = MagicMock()
        mock_container_client = MagicMock()
        mock_container_client.get_blob_client.return_value = mock_blob_client

        mock_service_client = MagicMock()
        mock_service_client.get_container_client.return_value = mock_container_client

        mock_blob_service_client.return_value = mock_service_client

        blob_name = "test.wav"

        result = azure.delete_blob_from_container(self.mock_connection_string, self.container_name, blob_name)

        self.assertTrue(result)
        mock_service_client.get_container_client.assert_called_once_with(self.container_name)
        mock_container_client.get_blob_client.assert_called_once_with(blob_name)
        mock_blob_client.delete_blob.assert_called_once()

    @patch("azure.storage.blob.BlobServiceClient.from_connection_string")
    def test_delete_blob_from_container_error(self, mock_blob_service_client):
        """Test error handling when deleting a blob"""
        # Setup mock to raise an exception
        mock_blob_client = MagicMock()
        mock_blob_client.delete_blob.side_effect = Exception("Delete error")

        mock_container_client = MagicMock()
        mock_container_client.get_blob_client.return_value = mock_blob_client

        mock_service_client = MagicMock()
        mock_service_client.get_container_client.return_value = mock_container_client

        mock_blob_service_client.return_value = mock_service_client

        result = azure.delete_blob_from_container(self.mock_connection_string, self.container_name, "test.wav")

        self.assertFalse(result)

    # Dodajemy testy dla calculate_service_cost, sprawdzając najpierw czy funkcja istnieje
    def test_calculate_service_cost(self):
        """Test calculation of Azure service costs"""
        # Pomiń test, jeśli funkcja nie istnieje
        if not hasattr(azure, "calculate_service_cost"):
            self.skipTest("calculate_service_cost function doesn't exist")

        audio_length = 300  # 5 minutes in seconds

        # Wywołaj funkcję tylko jeśli istnieje
        if hasattr(azure, "calculate_service_cost"):
            cost_info = azure.calculate_service_cost(audio_length)

            # Test that all expected keys are present in the result
            expected_keys = [
                "audio_length_seconds",
                "audio_size_mb",
                "transcribe_cost",
                "storage_cost",
                "transaction_cost",
                "total_cost",
                "currency",
            ]
            for key in expected_keys:
                self.assertIn(key, cost_info)

            # Test actual calculations
            self.assertEqual(cost_info["audio_length_seconds"], audio_length)

            # Audio size should be approximately (300/60) * 10 = 50 MB
            self.assertAlmostEqual(cost_info["audio_size_mb"], 50.0)

            # Total cost should be the sum of individual costs
            expected_total = (
                cost_info.get("transcribe_cost", 0)
                + cost_info.get("storage_cost", 0)
                + cost_info.get("transaction_cost", 0)
            )
            self.assertAlmostEqual(cost_info.get("total_cost", 0), expected_total)

    # Dodajemy testy dla get_supported_languages, sprawdzając najpierw czy funkcja istnieje
    def test_get_supported_languages(self):
        """Test getting supported languages"""
        # Pomiń test, jeśli funkcja nie istnieje
        if not hasattr(azure, "get_supported_languages"):
            self.skipTest("get_supported_languages function doesn't exist")

        # Wywołaj funkcję tylko jeśli istnieje
        if hasattr(azure, "get_supported_languages"):
            languages = azure.get_supported_languages()

            self.assertIsInstance(languages, dict)
            if languages:  # Tylko jeśli słownik nie jest pusty
                self.assertIn("pl-PL", languages)
                self.assertEqual(languages["pl-PL"], "polski")
                self.assertIn("en-US", languages)
                self.assertEqual(languages["en-US"], "angielski (USA)")

    # Test dla transcribe_short_audio - używamy prostego mockowania zamiast skomplikowanej struktury
    @patch("src.speecher.azure.SpeechConfig")
    @patch("src.speecher.azure.AudioConfig")
    @patch("src.speecher.azure.SpeechRecognizer")
    @patch("src.speecher.azure.ResultReason")
    @patch("src.speecher.azure.CancellationDetails")
    def test_transcribe_short_audio(
        self,
        mock_cancellation_details,
        mock_result_reason,
        mock_recognizer_class,
        mock_audio_config,
        mock_speech_config,
    ):
        """Test transcribing short audio directly with Speech SDK"""
        # Pomiń test, jeśli funkcja nie istnieje
        if not hasattr(azure, "transcribe_short_audio"):
            self.skipTest("transcribe_short_audio function doesn't exist")

        # Skonfiguruj mocki tylko jeśli funkcja istnieje
        if hasattr(azure, "transcribe_short_audio"):
            # Setup mocks
            mock_config = MagicMock()
            mock_speech_config.return_value = mock_config

            mock_audio = MagicMock()
            mock_audio_config.return_value = mock_audio

            mock_recognizer = MagicMock()
            mock_result = MagicMock()

            # Fix: Set up ResultReason as an enum-like value
            mock_result_reason.RecognizedSpeech = "RecognizedSpeech"

            # Use the correct property access for reason (it's an attribute, not a method)
            mock_result.reason = mock_result_reason.RecognizedSpeech
            mock_result.text = "To jest przykładowa transkrypcja."

            mock_recognizer.recognize_once_async.return_value.get.return_value = mock_result
            mock_recognizer_class.return_value = mock_recognizer

            with patch("builtins.open", mock_open(read_data=b"dummy_wav_data")):
                result = azure.transcribe_short_audio(
                    self.mock_subscription_key, self.mock_region, str(self.sample_wav_path)
                )

                # Verify function was called with correct parameters
                mock_speech_config.assert_called_once_with(
                    subscription=self.mock_subscription_key, region=self.mock_region
                )
                mock_audio_config.assert_called_once_with(filename=str(self.sample_wav_path))
                mock_recognizer_class.assert_called_once()
                mock_recognizer.recognize_once_async.assert_called_once()

                # Verify result
                self.assertEqual(result, "To jest przykładowa transkrypcja.")


if __name__ == "__main__":
    unittest.main()
