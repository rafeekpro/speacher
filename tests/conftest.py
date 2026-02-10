"""
Pytest configuration and fixtures for API tests
"""

import os
import sys
import tempfile
from datetime import datetime

import mongomock
import pytest
from bson.objectid import ObjectId
from fastapi.testclient import TestClient

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


@pytest.fixture
def mock_mongodb():
    """Create a mock MongoDB client"""
    return mongomock.MongoClient()


@pytest.fixture
def mock_collection(mock_mongodb):
    """Create a mock MongoDB collection"""
    db = mock_mongodb["test_db"]
    collection = db["test_collection"]
    return collection


@pytest.fixture
def sample_transcription():
    """Sample transcription data"""
    return {
        "_id": ObjectId(),
        "filename": "sample.wav",
        "provider": "aws",
        "language": "pl-PL",
        "transcript": "To jest przykładowa transkrypcja.",
        "speakers": [
            {"speaker": "Speaker 1", "text": "To jest przykładowa", "start_time": 0.0, "end_time": 2.5},
            {"speaker": "Speaker 2", "text": "transkrypcja", "start_time": 2.5, "end_time": 4.0},
        ],
        "enable_diarization": True,
        "max_speakers": 2,
        "duration": 4.0,
        "cost_estimate": 0.0016,
        "created_at": datetime.utcnow(),
        "file_size": 64000,
    }


@pytest.fixture
def sample_audio_file():
    """Create a sample audio file for testing"""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        # Write WAV header (simplified)
        f.write(b"RIFF")
        f.write((36 + 8).to_bytes(4, "little"))  # File size
        f.write(b"WAVE")
        f.write(b"fmt ")
        f.write((16).to_bytes(4, "little"))  # Subchunk size
        f.write((1).to_bytes(2, "little"))  # Audio format (PCM)
        f.write((1).to_bytes(2, "little"))  # Number of channels
        f.write((44100).to_bytes(4, "little"))  # Sample rate
        f.write((88200).to_bytes(4, "little"))  # Byte rate
        f.write((2).to_bytes(2, "little"))  # Block align
        f.write((16).to_bytes(2, "little"))  # Bits per sample
        f.write(b"data")
        f.write((8).to_bytes(4, "little"))  # Data chunk size
        f.write(b"\x00" * 8)  # Minimal audio data

        temp_path = f.name

    yield temp_path

    # Cleanup
    if os.path.exists(temp_path):
        os.remove(temp_path)


@pytest.fixture
def mock_aws_transcribe_response():
    """Mock AWS Transcribe API response"""
    return {
        "jobName": "test-job-123",
        "accountId": "123456789",
        "results": {
            "transcripts": [{"transcript": "Hello world this is a test transcription"}],
            "speaker_labels": {
                "speakers": 2,
                "segments": [
                    {
                        "start_time": "0.0",
                        "end_time": "2.5",
                        "speaker_label": "spk_0",
                        "items": [{"start_time": "0.0", "end_time": "0.5", "speaker_label": "spk_0"}],
                    },
                    {
                        "start_time": "2.5",
                        "end_time": "5.0",
                        "speaker_label": "spk_1",
                        "items": [{"start_time": "2.5", "end_time": "3.0", "speaker_label": "spk_1"}],
                    },
                ],
            },
            "items": [
                {
                    "start_time": "0.0",
                    "end_time": "0.5",
                    "alternatives": [{"confidence": "0.99", "content": "Hello"}],
                    "type": "pronunciation",
                },
                {
                    "start_time": "0.5",
                    "end_time": "1.0",
                    "alternatives": [{"confidence": "0.99", "content": "world"}],
                    "type": "pronunciation",
                },
            ],
        },
        "status": "COMPLETED",
    }


@pytest.fixture
def mock_azure_speech_response():
    """Mock Azure Speech Service response"""
    return {
        "recognitionStatus": "Success",
        "displayText": "To jest test Azure Speech Service.",
        "offset": 0,
        "duration": 30000000,  # 3 seconds in 100-nanosecond units
        "speakerResults": {
            "speakers": [
                {"speakerId": 1, "segments": [{"start": 0, "duration": 15000000, "text": "To jest test"}]},
                {
                    "speakerId": 2,
                    "segments": [{"start": 15000000, "duration": 15000000, "text": "Azure Speech Service"}],
                },
            ]
        },
    }


@pytest.fixture
def mock_gcp_speech_response():
    """Mock Google Cloud Speech-to-Text response"""
    return {
        "results": [
            {
                "alternatives": [{"transcript": "This is a Google Cloud test", "confidence": 0.98}],
                "resultEndTime": "4.5s",
                "languageCode": "en-US",
            }
        ],
        "totalBilledTime": "5s",
    }


@pytest.fixture
def mock_env_variables(monkeypatch):
    """Set mock environment variables for testing"""
    env_vars = {
        "MONGODB_URI": "mongodb://test:27017",
        "MONGODB_DB": "test_speecher",
        "MONGODB_COLLECTION": "test_transcriptions",
        "S3_BUCKET_NAME": "test-bucket",
        "AWS_ACCESS_KEY_ID": "test_key",
        "AWS_SECRET_ACCESS_KEY": "test_secret",
        "AWS_DEFAULT_REGION": "us-east-1",
        "AZURE_STORAGE_ACCOUNT": "test_account",
        "AZURE_STORAGE_KEY": "test_storage_key",
        "AZURE_CONTAINER_NAME": "test-container",
        "AZURE_SPEECH_KEY": "test_speech_key",
        "AZURE_SPEECH_REGION": "eastus",
        "GCP_PROJECT_ID": "test-project",
        "GCP_BUCKET_NAME": "test-gcp-bucket",
    }

    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

    return env_vars


@pytest.fixture
def multiple_transcriptions():
    """Generate multiple transcription records for testing"""
    transcriptions = []
    providers = ["aws", "azure", "gcp"]
    languages = ["pl-PL", "en-US", "de-DE"]

    for i in range(10):
        transcriptions.append(
            {
                "_id": ObjectId(),
                "filename": f"audio_{i}.wav",
                "provider": providers[i % 3],
                "language": languages[i % 3],
                "transcript": f"Transcription number {i}",
                "speakers": [
                    {"speaker": f"Speaker {j}", "text": f"Text {j}", "start_time": j * 2.0, "end_time": (j + 1) * 2.0}
                    for j in range(2)
                ],
                "enable_diarization": i % 2 == 0,
                "max_speakers": 2 + (i % 3),
                "duration": 10.0 + i,
                "cost_estimate": 0.024 * (10.0 + i) / 60,
                "created_at": datetime.utcnow(),
                "file_size": 100000 + i * 1000,
            }
        )

    return transcriptions


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    # Clear any existing data in the in-memory databases
    from backend.auth import api_keys_db, rate_limit_db, refresh_tokens_db, users_db
    from backend.database import projects_db, recordings_db, tags_db
    from backend.main import app

    users_db.clear()
    api_keys_db.clear()
    refresh_tokens_db.clear()
    rate_limit_db.clear()
    projects_db.clear()
    recordings_db.clear()
    tags_db.clear()

    return TestClient(app)


@pytest.fixture
def mock_cloud_services():
    """Mock all cloud service functions"""
    mocks = {}

    # AWS mocks
    with pytest.mock.patch("backend.main.aws_service") as aws_mock:
        aws_mock.upload_file_to_s3.return_value = True
        aws_mock.start_transcription_job.return_value = {"JobName": "test-job"}
        aws_mock.wait_for_job_completion.return_value = {
            "TranscriptionJob": {"Transcript": {"TranscriptFileUri": "https://test.uri"}}
        }
        aws_mock.download_transcription_result.return_value = {"results": {"transcripts": [{"transcript": "AWS test"}]}}
        aws_mock.delete_file_from_s3.return_value = True
        mocks["aws"] = aws_mock

    # Azure mocks
    with pytest.mock.patch("backend.main.azure_service") as azure_mock:
        azure_mock.upload_to_blob.return_value = "https://blob.url"
        azure_mock.transcribe_from_blob.return_value = {"displayText": "Azure test"}
        azure_mock.delete_blob.return_value = True
        mocks["azure"] = azure_mock

    # GCP mocks
    with pytest.mock.patch("backend.main.gcp_service") as gcp_mock:
        gcp_mock.upload_to_gcs.return_value = "gs://bucket/file"
        gcp_mock.transcribe_from_gcs.return_value = {"results": [{"alternatives": [{"transcript": "GCP test"}]}]}
        gcp_mock.delete_from_gcs.return_value = True
        mocks["gcp"] = gcp_mock

    return mocks
