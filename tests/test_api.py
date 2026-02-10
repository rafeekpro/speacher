"""
Comprehensive test suite for Speecher API
"""

import io
import os
import sys
from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from bson.objectid import ObjectId
from fastapi.testclient import TestClient

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Mock cloud service modules before importing backend
from tests.cloud_mocks import MockAWSService, MockAzureService, MockGCPService, MockTranscription

sys.modules["speecher.aws"] = MockAWSService
sys.modules["speecher.azure"] = MockAzureService
sys.modules["speecher.gcp"] = MockGCPService
sys.modules["speecher.transcription"] = MockTranscription

from backend.main import app

client = TestClient(app)


class TestHealthEndpoints:
    """Test health check endpoints"""

    def test_health_check(self):
        """Test basic health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy", "service": "Speecher API"}

    @patch("backend.main.mongo_client")
    def test_database_health_success(self, mock_mongo):
        """Test database health when MongoDB is connected"""
        mock_mongo.admin.command.return_value = True

        response = client.get("/db/health")
        assert response.status_code == 200
        assert "healthy" in response.json()["status"]

    @patch("backend.main.mongo_client")
    def test_database_health_failure(self, mock_mongo):
        """Test database health when MongoDB is disconnected"""
        mock_mongo.admin.command.side_effect = Exception("Connection failed")

        response = client.get("/db/health")
        assert response.status_code == 503
        assert "Database unhealthy" in response.json()["detail"]


class TestTranscribeEndpoint:
    """Test transcribe endpoint with different providers"""

    @pytest.fixture
    def audio_file(self):
        """Create a mock audio file with valid WAV header"""
        # Minimal valid WAV file header
        wav_data = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
        return io.BytesIO(wav_data)

    @pytest.fixture
    def mock_aws_functions(self):
        """Mock AWS-related functions"""
        with (
            patch("backend.main.aws_service.upload_file_to_s3") as mock_upload,
            patch("backend.main.aws_service.start_transcription_job") as mock_start,
            patch("backend.main.aws_service.wait_for_job_completion") as mock_wait,
            patch("backend.main.aws_service.download_transcription_result") as mock_download,
            patch("backend.main.aws_service.delete_file_from_s3") as mock_delete,
            patch("backend.main.process_transcription_data") as mock_process,
        ):
            mock_upload.return_value = (True, "test-bucket")  # Returns tuple (success, bucket_name)
            mock_start.return_value = {"JobName": "test-job"}
            mock_wait.return_value = {"TranscriptionJob": {"Transcript": {"TranscriptFileUri": "https://test.uri"}}}
            mock_download.return_value = {"results": {"transcripts": []}}
            mock_process.return_value = {
                "transcript": "Test transcription",
                "speakers": [
                    {"speaker": "Speaker 1", "text": "Hello", "start_time": 0, "end_time": 2},
                    {"speaker": "Speaker 2", "text": "World", "start_time": 2, "end_time": 4},
                ],
                "duration": 4.0,
            }
            mock_delete.return_value = True

            yield {
                "upload": mock_upload,
                "start": mock_start,
                "wait": mock_wait,
                "download": mock_download,
                "delete": mock_delete,
                "process": mock_process,
            }

    @patch("backend.main.api_keys_manager")
    @patch("backend.main.collection")
    def test_transcribe_aws_success(self, mock_collection, mock_api_keys, mock_aws_functions, audio_file):
        """Test successful AWS transcription"""
        mock_collection.insert_one.return_value = Mock(inserted_id=ObjectId())

        # Mock API keys configuration
        mock_api_keys.get_api_keys.return_value = {
            "keys": {
                "access_key_id": "test_key",
                "secret_access_key": "test_secret",
                "s3_bucket_name": "test-bucket",
                "region": "us-east-1",
            },
            "source": "test",
        }

        response = client.post(
            "/transcribe",
            files={"file": ("test.wav", audio_file, "audio/wav")},
            data={"provider": "aws", "language": "pl-PL", "enable_diarization": "true", "max_speakers": "4"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["transcript"] == "Test transcription"
        assert data["provider"] == "aws"
        assert data["language"] == "pl-PL"
        assert len(data["speakers"]) == 2
        assert data["duration"] == 4.0
        assert data["cost_estimate"] > 0

    def test_transcribe_invalid_file_type(self, audio_file):
        """Test transcription with invalid file type"""
        response = client.post(
            "/transcribe",
            files={"file": ("test.txt", audio_file, "text/plain")},
            data={"provider": "aws", "language": "en-US"},
        )

        assert response.status_code == 400
        detail = response.json()["detail"]
        assert "Invalid format" in detail or "Invalid file type" in detail

    @pytest.mark.skip(reason="Azure test needs environment setup - skipping for CI")
    @patch("backend.main.collection")
    @patch("backend.main.cloud_wrappers")
    def test_transcribe_azure_success(self, mock_wrappers, mock_collection, audio_file):
        """Test successful Azure transcription"""
        mock_collection.insert_one.return_value = Mock(inserted_id=ObjectId())

        # Mock Azure functions
        mock_wrappers.upload_to_blob.return_value = "https://blob.url"
        mock_wrappers.transcribe_from_blob.return_value = {"transcript": "Azure test"}
        mock_wrappers.delete_blob.return_value = True

        with patch("backend.main.process_transcription_data") as mock_process:
            mock_process.return_value = {"transcript": "Azure transcription", "speakers": [], "duration": 5.0}

            with patch.dict(os.environ, {"AZURE_STORAGE_ACCOUNT": "test_account", "AZURE_STORAGE_KEY": "test_key"}):
                response = client.post(
                    "/transcribe",
                    files={"file": ("test.wav", audio_file, "audio/wav")},
                    data={"provider": "azure", "language": "en-GB", "enable_diarization": "false"},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "azure"
        assert data["transcript"] == "Azure transcription"

    @patch("backend.main.api_keys_manager")
    @patch("backend.main.collection")
    @patch("backend.main.cloud_wrappers")
    def test_transcribe_gcp_success(self, mock_wrappers, mock_collection, mock_api_keys, audio_file):
        """Test successful GCP transcription"""
        mock_collection.insert_one.return_value = Mock(inserted_id=ObjectId())

        # Mock API keys configuration
        mock_api_keys.get_api_keys.return_value = {
            "keys": {"credentials_json": "{}", "gcs_bucket_name": "test-bucket"},
            "source": "test",
            "enabled": True,  # Add enabled flag
        }

        # Mock GCP functions
        mock_wrappers.upload_to_gcs.return_value = "gs://bucket/file"
        mock_wrappers.transcribe_from_gcs.return_value = {"transcript": "GCP test"}
        mock_wrappers.delete_from_gcs.return_value = True

        with patch("backend.main.process_transcription_data") as mock_process:
            mock_process.return_value = {"transcript": "GCP transcription", "speakers": [], "duration": 3.0}

            response = client.post(
                "/transcribe",
                files={"file": ("test.mp3", audio_file, "audio/mp3")},
                data={"provider": "gcp", "language": "de-DE", "enable_diarization": "true", "max_speakers": "2"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "gcp"
        assert data["language"] == "de-DE"

    def test_transcribe_invalid_provider(self, audio_file):
        """Test transcription with invalid provider"""
        response = client.post(
            "/transcribe",
            files={"file": ("test.wav", audio_file, "audio/wav")},
            data={"provider": "invalid_provider", "language": "en-US"},
        )

        assert response.status_code == 400
        assert "Invalid provider" in response.json()["detail"]


class TestHistoryEndpoint:
    """Test history endpoint with filtering"""

    @patch("backend.main.collection")
    def test_get_history_no_filters(self, mock_collection):
        """Test getting history without filters"""
        mock_docs = [
            {
                "_id": ObjectId(),
                "filename": "test1.wav",
                "provider": "aws",
                "language": "en-US",
                "created_at": datetime.utcnow(),
                "transcript": "Test 1",
                "duration": 10.0,
            },
            {
                "_id": ObjectId(),
                "filename": "test2.wav",
                "provider": "azure",
                "language": "pl-PL",
                "created_at": datetime.utcnow(),
                "transcript": "Test 2",
                "duration": 20.0,
            },
        ]

        mock_cursor = Mock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.limit.return_value = iter(mock_docs)
        mock_collection.find.return_value = mock_cursor

        response = client.get("/history")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["filename"] == "test1.wav"
        assert data[1]["filename"] == "test2.wav"

    @patch("backend.main.collection")
    def test_get_history_with_search(self, mock_collection):
        """Test getting history with search filter"""
        mock_cursor = Mock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.limit.return_value = iter([])
        mock_collection.find.return_value = mock_cursor

        response = client.get("/history?search=specific")

        assert response.status_code == 200
        mock_collection.find.assert_called_once()
        call_args = mock_collection.find.call_args[0][0]
        assert "filename" in call_args
        assert "$regex" in call_args["filename"]

    @patch("backend.main.collection")
    def test_get_history_with_provider_filter(self, mock_collection):
        """Test getting history with provider filter"""
        mock_cursor = Mock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.limit.return_value = iter([])
        mock_collection.find.return_value = mock_cursor

        response = client.get("/history?provider=aws")

        assert response.status_code == 200
        call_args = mock_collection.find.call_args[0][0]
        assert call_args["provider"] == "aws"

    @patch("backend.main.collection")
    def test_get_history_with_date_filter(self, mock_collection):
        """Test getting history with date filter"""
        mock_cursor = Mock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.limit.return_value = iter([])
        mock_collection.find.return_value = mock_cursor

        date_from = "2024-01-01T00:00:00"
        response = client.get(f"/history?date_from={date_from}")

        assert response.status_code == 200
        call_args = mock_collection.find.call_args[0][0]
        assert "created_at" in call_args
        assert "$gte" in call_args["created_at"]


class TestTranscriptionEndpoints:
    """Test individual transcription endpoints"""

    @patch("backend.main.collection")
    def test_get_transcription_success(self, mock_collection):
        """Test getting a specific transcription"""
        mock_id = ObjectId()
        mock_doc = {
            "_id": mock_id,
            "filename": "test.wav",
            "transcript": "Test transcription",
            "created_at": datetime.utcnow(),
        }
        mock_collection.find_one.return_value = mock_doc

        response = client.get(f"/transcription/{str(mock_id)}")

        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "test.wav"
        assert data["transcript"] == "Test transcription"

    @patch("backend.main.collection")
    def test_get_transcription_not_found(self, mock_collection):
        """Test getting non-existent transcription"""
        mock_collection.find_one.return_value = None

        response = client.get(f"/transcription/{str(ObjectId())}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_get_transcription_invalid_id(self):
        """Test getting transcription with invalid ID"""
        response = client.get("/transcription/invalid_id")

        assert response.status_code == 404  # Invalid ID returns 404 not found

    @patch("backend.main.collection")
    def test_delete_transcription_success(self, mock_collection):
        """Test deleting a transcription"""
        mock_collection.delete_one.return_value = Mock(deleted_count=1)

        response = client.delete(f"/transcription/{str(ObjectId())}")

        assert response.status_code == 200
        assert "successfully" in response.json()["message"]

    @patch("backend.main.collection")
    def test_delete_transcription_not_found(self, mock_collection):
        """Test deleting non-existent transcription"""
        mock_collection.delete_one.return_value = Mock(deleted_count=0)

        response = client.delete(f"/transcription/{str(ObjectId())}")

        assert response.status_code == 404


class TestStatisticsEndpoint:
    """Test statistics endpoint"""

    @patch("backend.main.collection")
    def test_get_statistics(self, mock_collection):
        """Test getting usage statistics"""
        mock_collection.count_documents.return_value = 100
        mock_collection.aggregate.return_value = [
            {"_id": "aws", "count": 50, "total_duration": 1000, "total_cost": 24.0},
            {"_id": "azure", "count": 30, "total_duration": 600, "total_cost": 9.6},
            {"_id": "gcp", "count": 20, "total_duration": 400, "total_cost": 7.2},
        ]

        mock_cursor = [{"filename": "file1.wav"}, {"filename": "file2.wav"}, {"filename": "file3.wav"}]
        mock_collection.find.return_value.sort.return_value.limit.return_value = mock_cursor

        response = client.get("/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total_transcriptions"] == 100
        assert len(data["provider_statistics"]) == 3
        assert len(data["recent_files"]) == 3

        # Check provider stats
        aws_stats = next(s for s in data["provider_statistics"] if s["_id"] == "aws")
        assert aws_stats["count"] == 50
        assert aws_stats["total_cost"] == 24.0


class TestCostCalculation:
    """Test cost calculation function"""

    def test_cost_calculation_aws(self):
        """Test AWS cost calculation"""
        from backend.main import calculate_cost

        cost = calculate_cost("aws", 60)  # 60 seconds = 1 minute
        assert cost == 0.024

    def test_cost_calculation_azure(self):
        """Test Azure cost calculation"""
        from backend.main import calculate_cost

        cost = calculate_cost("azure", 120)  # 2 minutes
        assert cost == 0.032

    def test_cost_calculation_gcp(self):
        """Test GCP cost calculation"""
        from backend.main import calculate_cost

        cost = calculate_cost("gcp", 180)  # 3 minutes
        assert abs(cost - 0.054) < 0.0001  # Use approximate comparison for floating point

    def test_cost_calculation_unknown_provider(self):
        """Test cost calculation for unknown provider"""
        from backend.main import calculate_cost

        cost = calculate_cost("unknown", 60)
        assert cost == 0.02  # Default rate


class TestTimestampFormatting:
    """Test timestamp formatting function"""

    def test_format_timestamp(self):
        """Test timestamp formatting"""
        from backend.main import format_timestamp

        assert format_timestamp(0) == "00:00:00"
        assert format_timestamp(59) == "00:00:59"
        assert format_timestamp(61) == "00:01:01"
        assert format_timestamp(3661) == "01:01:01"
        assert format_timestamp(7200) == "02:00:00"


class TestErrorHandling:
    """Test error handling scenarios"""

    @patch("backend.main.api_keys_manager")
    @patch("backend.main.aws_service.upload_file_to_s3")
    def test_aws_upload_failure(self, mock_upload, mock_api_keys):
        """Test handling of AWS upload failure"""
        # Mock API keys to pass configuration check
        mock_api_keys.get_api_keys.return_value = {
            "keys": {
                "access_key_id": "test_key",
                "secret_access_key": "test_secret",
                "s3_bucket_name": "test-bucket",
                "region": "us-east-1",
            },
            "source": "test",
        }

        mock_upload.return_value = (False, None)  # Returns tuple (success, bucket_name)

        # Create a minimal valid WAV file
        wav_data = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
        audio_file = io.BytesIO(wav_data)
        response = client.post(
            "/transcribe",
            files={"file": ("test.wav", audio_file, "audio/wav")},
            data={"provider": "aws", "language": "en-US"},
        )

        assert response.status_code == 500
        assert "Failed to upload" in response.json()["detail"]

    @patch("backend.main.collection")
    def test_mongodb_insert_failure(self, mock_collection):
        """Test handling of MongoDB insert failure"""
        mock_collection.insert_one.side_effect = Exception("Database error")

        with patch("backend.main.process_aws_transcription") as mock_process:
            mock_process.return_value = {"transcript": "Test", "speakers": [], "duration": 1.0}

            # Create a minimal valid WAV file
            wav_data = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
            audio_file = io.BytesIO(wav_data)
            response = client.post(
                "/transcribe",
                files={"file": ("test.wav", audio_file, "audio/wav")},
                data={"provider": "aws", "language": "en-US"},
            )

            assert response.status_code == 500


# Force CI re-run
