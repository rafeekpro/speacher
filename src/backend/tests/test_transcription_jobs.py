"""
Tests for TranscriptionJobManager - Real-time job tracking.

Tests follow TDD: RED (write failing test), GREEN (make it pass), REFACTOR (improve).
"""

import pytest
import time
import uuid
from src.backend.transcription_jobs import TranscriptionJobManager, JobStatus


class TestTranscriptionJobManager:
    """Test suite for TranscriptionJobManager class."""

    def test_create_job_returns_unique_id(self, job_manager):
        """Test that creating a job returns a unique job ID."""
        user_id = "user123"
        filename = "test.mp3"
        provider = "aws"

        job_id = job_manager.create_job(user_id, filename, provider)

        assert job_id is not None
        assert isinstance(job_id, str)
        # Should be a UUID
        uuid.UUID(job_id)  # Will raise ValueError if not a valid UUID

    def test_create_job_stores_initial_state(self, job_manager):
        """Test that creating a job stores correct initial state."""
        user_id = "user123"
        filename = "test.mp3"
        provider = "aws"

        job_id = job_manager.create_job(user_id, filename, provider)
        job = job_manager.get_job_status(job_id)

        assert job is not None
        assert job["user_id"] == user_id
        assert job["filename"] == filename
        assert job["provider"] == provider
        assert job["status"] == JobStatus.CREATED
        assert job["progress"] == 0
        assert job["current_step"] == "Job created"
        assert job["cost_estimate"] == 0.0
        assert "created_at" in job

    def test_create_multiple_jobs_have_unique_ids(self, job_manager):
        """Test that multiple jobs have unique IDs."""
        user_id = "user123"

        job_id_1 = job_manager.create_job(user_id, "test1.mp3", "aws")
        job_id_2 = job_manager.create_job(user_id, "test2.mp3", "aws")

        assert job_id_1 != job_id_2

    def test_update_progress_changes_values(self, job_manager):
        """Test that updating progress changes job values."""
        job_id = job_manager.create_job("user123", "test.mp3", "aws")

        job_manager.update_progress(
            job_id=job_id,
            progress=50,
            status=JobStatus.PROCESSING,
            current_step="Processing audio",
            cost_estimate=0.05
        )

        job = job_manager.get_job_status(job_id)

        assert job["progress"] == 50
        assert job["status"] == JobStatus.PROCESSING
        assert job["current_step"] == "Processing audio"
        assert job["cost_estimate"] == 0.05

    def test_update_progress_clamps_to_100(self, job_manager):
        """Test that progress is clamped to maximum 100."""
        job_id = job_manager.create_job("user123", "test.mp3", "aws")

        job_manager.update_progress(
            job_id=job_id,
            progress=150,  # Over 100
            status=JobStatus.PROCESSING,
            current_step="Processing"
        )

        job = job_manager.get_job_status(job_id)
        assert job["progress"] == 100

    def test_update_progress_clamps_to_0(self, job_manager):
        """Test that progress is clamped to minimum 0."""
        job_id = job_manager.create_job("user123", "test.mp3", "aws")

        job_manager.update_progress(
            job_id=job_id,
            progress=-10,  # Under 0
            status=JobStatus.PROCESSING,
            current_step="Processing"
        )

        job = job_manager.get_job_status(job_id)
        assert job["progress"] == 0

    def test_update_nonexistent_job_raises_error(self, job_manager):
        """Test that updating a nonexistent job raises KeyError."""
        with pytest.raises(KeyError, match="Job not found"):
            job_manager.update_progress(
                job_id="nonexistent-job-id",
                progress=50,
                status=JobStatus.PROCESSING,
                current_step="Processing",
                cost_estimate=0.0
            )

    def test_get_job_status_returns_complete_data(self, job_manager):
        """Test that get_job_status returns all expected fields."""
        job_id = job_manager.create_job("user123", "test.mp3", "aws")

        job_manager.update_progress(
            job_id=job_id,
            progress=75,
            status=JobStatus.PROCESSING,
            current_step="Transcribing",
            cost_estimate=0.08
        )

        job = job_manager.get_job_status(job_id)

        expected_keys = {
            "job_id", "user_id", "filename", "provider",
            "status", "progress", "current_step",
            "cost_estimate", "created_at", "updated_at", "duration"
        }

        assert set(job.keys()) == expected_keys
        assert job["job_id"] == job_id

    def test_get_nonexistent_job_returns_none(self, job_manager):
        """Test that getting a nonexistent job returns None."""
        job = job_manager.get_job_status("nonexistent-job-id")
        assert job is None

    def test_complete_job_sets_final_state(self, job_manager):
        """Test that completing a job sets correct final state."""
        job_id = job_manager.create_job("user123", "test.mp3", "aws")

        job_manager.update_progress(
            job_id=job_id,
            progress=100,
            status=JobStatus.COMPLETED,
            current_step="Completed",
            cost_estimate=0.12
        )

        job = job_manager.get_job_status(job_id)

        assert job["progress"] == 100
        assert job["status"] == JobStatus.COMPLETED
        assert job["current_step"] == "Completed"

    def test_failed_job_sets_error_state(self, job_manager):
        """Test that failing a job sets error state."""
        job_id = job_manager.create_job("user123", "test.mp3", "aws")

        job_manager.update_progress(
            job_id=job_id,
            progress=45,
            status=JobStatus.FAILED,
            current_step="Error: AWS service unavailable",
            cost_estimate=0.0
        )

        job = job_manager.get_job_status(job_id)

        assert job["status"] == JobStatus.FAILED
        assert "Error" in job["current_step"]

    def test_updated_at_timestamp_changes(self, job_manager):
        """Test that updated_at timestamp changes on each update."""
        job_id = job_manager.create_job("user123", "test.mp3", "aws")

        # Get initial timestamp
        initial_timestamp = job_manager.get_job_status(job_id)["updated_at"]
        time.sleep(0.1)  # Delay to ensure timestamp difference

        job_manager.update_progress(
            job_id=job_id,
            progress=25,
            status=JobStatus.UPLOADING,
            current_step="Uploading"
        )

        # Get updated timestamp
        updated_timestamp = job_manager.get_job_status(job_id)["updated_at"]

        assert updated_timestamp > initial_timestamp

    def test_get_all_jobs_for_user(self, job_manager):
        """Test retrieving all jobs for a specific user."""
        user_id = "user123"

        job_id_1 = job_manager.create_job(user_id, "test1.mp3", "aws")
        job_id_2 = job_manager.create_job(user_id, "test2.mp3", "aws")
        job_manager.create_job("other_user", "test3.mp3", "aws")  # Different user

        user_jobs = job_manager.get_user_jobs(user_id)

        assert len(user_jobs) == 2
        job_ids = [job["job_id"] for job in user_jobs]
        assert job_id_1 in job_ids
        assert job_id_2 in job_ids

    def test_delete_job_removes_from_storage(self, job_manager):
        """Test that deleting a job removes it from storage."""
        job_id = job_manager.create_job("user123", "test.mp3", "aws")

        assert job_manager.get_job_status(job_id) is not None

        job_manager.delete_job(job_id)

        assert job_manager.get_job_status(job_id) is None

    def test_delete_nonexistent_job_is_idempotent(self, job_manager):
        """Test that deleting a nonexistent job doesn't raise error."""
        # Should not raise an exception
        job_manager.delete_job("nonexistent-job-id")

    def test_job_status_enum_values(self):
        """Test that JobStatus enum has expected values."""
        assert JobStatus.CREATED.value == "created"
        assert JobStatus.UPLOADING.value == "uploading"
        assert JobStatus.QUEUED.value == "queued"
        assert JobStatus.PROCESSING.value == "processing"
        assert JobStatus.DOWNLOADING.value == "downloading"
        assert JobStatus.COMPLETED.value == "completed"
        assert JobStatus.FAILED.value == "failed"


@pytest.fixture
def job_manager():
    """Create a fresh TranscriptionJobManager for each test."""
    manager = TranscriptionJobManager()
    yield manager
    # Cleanup: delete all jobs after test
    for job_id in list(manager.jobs.keys()):
        manager.delete_job(job_id)
