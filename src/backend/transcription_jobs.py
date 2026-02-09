"""
Transcription job manager for real-time progress tracking.

Manages in-memory storage of transcription job state and progress.
"""

import time
import uuid
from enum import Enum
from typing import Dict, List, Optional


class JobStatus(str, Enum):
    """Enumeration of possible job statuses."""

    CREATED = "created"
    UPLOADING = "uploading"
    QUEUED = "queued"
    PROCESSING = "processing"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"


class TranscriptionJobManager:
    """Manages transcription job state and progress tracking.

    Jobs are stored in memory with complete state tracking including
    progress percentage, current status, step descriptions, and cost estimates.
    """

    def __init__(self):
        """Initialize the job manager with empty job storage."""
        self.jobs: Dict[str, Dict] = {}

    def create_job(
        self, user_id: str, filename: str, provider: str, duration: float = None, initial_cost_estimate: float = 0.0
    ) -> str:
        """Create a new transcription job.

        Args:
            user_id: User ID creating the job
            filename: Name of the file being transcribed
            provider: Cloud provider (aws, azure, gcp)
            duration: Audio duration in seconds (optional, can be updated later)
            initial_cost_estimate: Initial cost estimate based on duration (default: 0.0)

        Returns:
            Unique job ID (UUID string)
        """
        job_id = str(uuid.uuid4())
        now = time.time_ns() / 1e9  # Convert nanoseconds to seconds

        self.jobs[job_id] = {
            "job_id": job_id,
            "user_id": user_id,
            "filename": filename,
            "provider": provider,
            "status": JobStatus.CREATED,
            "progress": 0,
            "current_step": "Job created",
            "cost_estimate": initial_cost_estimate,
            "duration": duration,  # Audio duration in seconds
            "created_at": now,
            "updated_at": now,
        }

        return job_id

    def update_progress(
        self,
        job_id: str,
        progress: float,
        status: JobStatus,
        current_step: str,
        cost_estimate: float = 0.0,
        duration: float = None,
    ) -> None:
        """Update job progress and status.

        Args:
            job_id: Job ID to update
            progress: Progress percentage (0-100, will be clamped)
            status: New job status
            current_step: Description of current step
            cost_estimate: Estimated cost in USD
            duration: Audio duration in seconds (optional, for updating later)

        Raises:
            KeyError: If job_id not found
        """
        if job_id not in self.jobs:
            raise KeyError(f"Job not found: {job_id}")

        # Clamp progress to valid range
        progress = max(0, min(100, progress))

        update_data = {
            "progress": progress,
            "status": status,
            "current_step": current_step,
            "cost_estimate": cost_estimate,
            "updated_at": time.time_ns() / 1e9,  # Convert nanoseconds to seconds
        }

        # Only update duration if provided
        if duration is not None:
            update_data["duration"] = duration

        self.jobs[job_id].update(update_data)

    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get complete status information for a job.

        Args:
            job_id: Job ID to query

        Returns:
            Job status dict with all fields, or None if not found
        """
        return self.jobs.get(job_id)

    def get_user_jobs(self, user_id: str) -> List[Dict]:
        """Get all jobs for a specific user.

        Args:
            user_id: User ID to query

        Returns:
            List of job dicts for the user
        """
        return [job for job in self.jobs.values() if job["user_id"] == user_id]

    def delete_job(self, job_id: str) -> None:
        """Delete a job from storage.

        Args:
            job_id: Job ID to delete

        Note:
            Does not raise an error if job_id not found (idempotent)
        """
        self.jobs.pop(job_id, None)
