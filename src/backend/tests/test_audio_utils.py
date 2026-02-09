"""
Tests for audio_utils.py - Audio duration detection functionality.

Tests follow TDD principles:
1. Test duration detection for various audio formats
2. Test error handling for corrupted/invalid files
3. Test with sample audio files
"""

import os
import tempfile
import pytest
import wave

from backend.audio_utils import get_audio_duration, LIBROSA_AVAILABLE


class TestAudioDurationDetection:
    """Test suite for audio duration detection."""

    def test_get_duration_nonexistent_file(self):
        """Test error handling for nonexistent file."""
        with pytest.raises(FileNotFoundError):
            get_audio_duration("/nonexistent/file.wav")

    def test_get_duration_empty_file(self):
        """Test error handling for empty file."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
            # File is empty

        try:
            # Empty file check happens before librosa check
            with pytest.raises(ValueError, match="Audio file is empty"):
                get_audio_duration(tmp_path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_get_duration_no_librosa(self):
        """Test error handling when librosa is not installed."""
        # Temporarily set LIBROSA_AVAILABLE to False
        import backend.audio_utils as audio_utils_module

        original_value = audio_utils_module.LIBROSA_AVAILABLE
        original_librosa = audio_utils_module.librosa

        try:
            # Mock librosa as unavailable
            audio_utils_module.LIBROSA_AVAILABLE = False
            audio_utils_module.librosa = None

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name
                tmp.write(b"fake audio")

            try:
                with pytest.raises(ImportError, match="librosa is not installed"):
                    get_audio_duration(tmp_path)
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

        finally:
            # Restore original values
            audio_utils_module.LIBROSA_AVAILABLE = original_value
            audio_utils_module.librosa = original_librosa


@pytest.mark.skipif(not LIBROSA_AVAILABLE, reason="librosa not installed")
class TestAudioDurationWithLibrosa:
    """Tests that require librosa to be installed."""

    def test_get_duration_from_wav_file(self):
        """Test duration detection from valid WAV file."""
        # Create a temporary WAV file with known duration
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Create a 1-second WAV file (44100 Hz, 16-bit, mono)
            sample_rate = 44100
            duration_seconds = 1.0
            num_frames = int(sample_rate * duration_seconds)

            with wave.open(tmp_path, "w") as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(sample_rate)
                wav_file.setnframes(num_frames)
                # Write silence (zeros)
                wav_file.writeframes(b"\x00\x00" * num_frames)

            # Test duration detection
            duration = get_audio_duration(tmp_path)

            # Assert duration is approximately 1 second (±0.1s tolerance)
            assert abs(duration - 1.0) < 0.1, f"Expected ~1.0s, got {duration}s"

        finally:
            # Cleanup
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_get_duration_corrupted_file(self):
        """Test error handling for corrupted audio file."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
            tmp.write(b"corrupted audio data that is not valid")

        try:
            with pytest.raises(Exception):
                get_audio_duration(tmp_path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_get_duration_long_audio(self):
        """Test duration detection for longer audio file (5 minutes)."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Create a valid WAV file header for 5 minutes
            sample_rate = 44100
            duration_seconds = 300.0  # 5 minutes
            num_frames = int(sample_rate * duration_seconds)

            with wave.open(tmp_path, "w") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.setnframes(num_frames)

            # Test duration detection
            duration = get_audio_duration(tmp_path)

            # Assert duration is approximately 300 seconds
            assert abs(duration - 300.0) < 1.0, f"Expected ~300.0s, got {duration}s"

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


@pytest.mark.skipif(not LIBROSA_AVAILABLE, reason="librosa not installed")
class TestAudioDurationEdgeCases:
    """Test edge cases for audio duration detection."""

    def test_very_short_audio(self):
        """Test duration detection for very short audio (< 1 second)."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            sample_rate = 44100
            duration_seconds = 0.5  # Half second
            num_frames = int(sample_rate * duration_seconds)

            with wave.open(tmp_path, "w") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.setnframes(num_frames)

            duration = get_audio_duration(tmp_path)
            assert abs(duration - 0.5) < 0.1, f"Expected ~0.5s, got {duration}s"

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_stereo_audio(self):
        """Test duration detection for stereo audio."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            sample_rate = 44100
            duration_seconds = 2.0
            num_frames = int(sample_rate * duration_seconds)

            with wave.open(tmp_path, "w") as wav_file:
                wav_file.setnchannels(2)  # Stereo
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.setnframes(num_frames)

            duration = get_audio_duration(tmp_path)
            assert abs(duration - 2.0) < 0.1, f"Expected ~2.0s, got {duration}s"

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
