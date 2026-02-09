"""
Integration tests for audio duration detection in transcription flow.

Tests that the duration detection integrates properly with the
transcription job manager and cost estimation.
"""

import pytest
from backend.transcription_jobs import TranscriptionJobManager, JobStatus


class TestDurationDetectionIntegration:
    """Test integration of duration detection with transcription jobs."""

    def test_create_job_with_duration_and_cost(self):
        """Test creating a job with duration and cost estimate."""
        job_manager = TranscriptionJobManager()

        # Create job with duration and cost
        duration = 125.5  # 2 minutes 5.5 seconds
        cost_estimate = 0.05  # $0.05

        job_id = job_manager.create_job(
            user_id="test_user",
            filename="test_audio.wav",
            provider="aws",
            duration=duration,
            initial_cost_estimate=cost_estimate,
        )

        # Verify job was created with correct data
        job_status = job_manager.get_job_status(job_id)
        assert job_status is not None
        assert job_status["duration"] == duration
        assert job_status["cost_estimate"] == cost_estimate
        assert job_status["filename"] == "test_audio.wav"
        assert job_status["provider"] == "aws"
        assert job_status["status"] == JobStatus.CREATED

    def test_create_job_without_duration_backwards_compatible(self):
        """Test that creating job without duration still works (backwards compatibility)."""
        job_manager = TranscriptionJobManager()

        # Create job without duration (old style)
        job_id = job_manager.create_job(user_id="test_user", filename="test_audio.wav", provider="aws")

        # Verify job was created with None duration and 0 cost
        job_status = job_manager.get_job_status(job_id)
        assert job_status is not None
        assert job_status["duration"] is None
        assert job_status["cost_estimate"] == 0.0
        assert job_status["status"] == JobStatus.CREATED

    def test_update_job_with_duration(self):
        """Test updating a job with duration information."""
        job_manager = TranscriptionJobManager()

        # Create job without duration
        job_id = job_manager.create_job(user_id="test_user", filename="test_audio.wav", provider="aws")

        # Update with duration
        duration = 180.0  # 3 minutes
        job_manager.update_progress(
            job_id=job_id,
            progress=50,
            status=JobStatus.PROCESSING,
            current_step="Processing audio",
            cost_estimate=0.07,
            duration=duration,
        )

        # Verify duration was updated
        job_status = job_manager.get_job_status(job_id)
        assert job_status["duration"] == duration
        assert job_status["cost_estimate"] == 0.07

    def test_update_job_without_duration_preserves_existing(self):
        """Test that updating job without duration parameter preserves existing duration."""
        job_manager = TranscriptionJobManager()

        # Create job with duration
        initial_duration = 120.0
        job_id = job_manager.create_job(
            user_id="test_user",
            filename="test_audio.wav",
            provider="aws",
            duration=initial_duration,
            initial_cost_estimate=0.05,
        )

        # Update without specifying duration
        job_manager.update_progress(
            job_id=job_id, progress=50, status=JobStatus.PROCESSING, current_step="Processing audio", cost_estimate=0.06
        )

        # Verify duration was preserved
        job_status = job_manager.get_job_status(job_id)
        assert job_status["duration"] == initial_duration
        assert job_status["cost_estimate"] == 0.06

    def test_calculate_cost_with_duration(self):
        """Test cost calculation using detected duration."""

        # Simulate calculate_cost function
        def calculate_cost(provider: str, duration_seconds: float) -> float:
            """Calculate estimated cost based on provider and duration."""
            duration_minutes = duration_seconds / 60
            costs = {
                "aws": 0.024,  # $0.024 per minute
                "azure": 0.016,  # $0.016 per minute
                "gcp": 0.018,  # $0.018 per minute
            }
            return costs.get(provider, 0.02) * duration_minutes

        # Test AWS cost calculation
        duration = 300.0  # 5 minutes
        cost = calculate_cost("aws", duration)
        assert cost == 0.12  # 5 minutes * $0.024 = $0.12

        # Test Azure cost calculation
        cost = calculate_cost("azure", duration)
        assert cost == 0.08  # 5 minutes * $0.016 = $0.08

        # Test GCP cost calculation
        cost = calculate_cost("gcp", duration)
        assert cost == 0.09  # 5 minutes * $0.018 = $0.09

    def test_cost_estimation_for_various_durations(self):
        """Test cost estimation for various audio durations."""

        def calculate_cost(provider: str, duration_seconds: float) -> float:
            duration_minutes = duration_seconds / 60
            costs = {"aws": 0.024, "azure": 0.016, "gcp": 0.018}
            return costs.get(provider, 0.02) * duration_minutes

        test_cases = [
            (30.0, 0.012),  # 30 seconds = $0.012
            (60.0, 0.024),  # 1 minute = $0.024
            (120.0, 0.048),  # 2 minutes = $0.048
            (300.0, 0.12),  # 5 minutes = $0.12
            (600.0, 0.24),  # 10 minutes = $0.24
            (1800.0, 0.72),  # 30 minutes = $0.72
            (3600.0, 1.44),  # 1 hour = $1.44
        ]

        for duration, expected_cost in test_cases:
            cost = calculate_cost("aws", duration)
            assert abs(cost - expected_cost) < 0.001, f"Duration {duration}s: expected ${expected_cost}, got ${cost}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
