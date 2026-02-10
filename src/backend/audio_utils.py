"""
Audio utilities for duration detection and validation.

Provides functionality to detect audio duration from various formats
including WAV, MP3, M4A, FLAC, and OGG using librosa.
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Import librosa at module level for easier testing
try:
    import librosa

    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    librosa = None
    logger.warning("librosa not available - audio duration detection will fail")


def get_audio_duration(file_path: str) -> float:
    """Detect audio duration in seconds.

    Uses librosa to load audio metadata and calculate duration.
    Supports various audio formats: WAV, MP3, M4A, FLAC, OGG.

    Args:
        file_path: Path to the audio file

    Returns:
        Duration in seconds as a float

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file is empty or corrupted
        ImportError: If librosa is not installed
        Exception: For other audio processing errors

    Example:
        >>> duration = get_audio_duration("sample.wav")
        >>> print(f"Duration: {duration:.2f} seconds")
        Duration: 125.50 seconds
    """
    # Check if file exists FIRST (before checking librosa)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    # Check if file is empty
    if os.path.getsize(file_path) == 0:
        raise ValueError(f"Audio file is empty: {file_path}")

    # Check if librosa is available
    if not LIBROSA_AVAILABLE or librosa is None:
        raise ImportError("librosa is not installed. Install with: pip install librosa")

    try:
        # Load audio file with native sample rate (sr=None)
        # This returns the audio time series as a numpy array and the sample rate
        y, sr = librosa.load(file_path, sr=None)

        # Calculate duration: number of samples / sample rate
        # Handle both mono (1D array) and stereo (2D array)
        if y.ndim == 1:
            # Mono audio
            duration = len(y) / sr
        else:
            # Stereo or multi-channel audio (shape: [samples, channels])
            duration = y.shape[0] / sr

        logger.info(f"Detected audio duration: {duration:.2f}s from {file_path}")
        return duration

    except FileNotFoundError:
        # Re-raise FileNotFoundError as-is
        raise
    except ValueError as e:
        # Re-raise ValueError with context
        raise ValueError(f"Invalid audio file {file_path}: {str(e)}")
    except Exception as e:
        # Catch any other exceptions from librosa
        logger.error(f"Failed to detect audio duration for {file_path}: {e}")
        raise Exception(f"Audio processing error for {file_path}: {str(e)}")


def get_audio_duration_fast(file_path: str) -> Optional[float]:
    """Fast audio duration detection using only metadata (no full audio load).

    This is an optimization for large files where we only need duration.
    Uses librosa's get_duration() which reads only file headers.

    Args:
        file_path: Path to the audio file

    Returns:
        Duration in seconds, or None if detection fails

    Note:
        This function is more memory-efficient for large files but may
        be less accurate for some formats. For critical applications,
        use get_audio_duration() instead.
    """
    if not LIBROSA_AVAILABLE or librosa is None:
        logger.error("librosa not available for fast duration detection")
        return None

    try:
        # Use librosa's get_duration for fast metadata-only reading
        duration = librosa.get_duration(filename=file_path)

        if duration > 0:
            logger.info(f"Fast duration detection: {duration:.2f}s from {file_path}")
            return duration
        else:
            logger.warning(f"Invalid duration detected: {duration}s from {file_path}")
            return None

    except Exception as e:
        logger.error(f"Fast duration detection failed for {file_path}: {e}")
        return None


def validate_audio_file(file_path: str, min_duration: float = 0.1, max_duration: float = 7200.0) -> tuple[bool, str]:
    """Validate audio file meets duration requirements.

    Args:
        file_path: Path to the audio file
        min_duration: Minimum duration in seconds (default: 0.1s)
        max_duration: Maximum duration in seconds (default: 2 hours)

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        >>> is_valid, error = validate_audio_file("sample.wav", min_duration=1.0)
        >>> if not is_valid:
        ...     print(f"Invalid: {error}")
    """
    try:
        duration = get_audio_duration(file_path)

        if duration < min_duration:
            return False, f"Audio duration ({duration:.2f}s) is too short. Minimum: {min_duration}s"

        if duration > max_duration:
            return False, f"Audio duration ({duration:.2f}s) is too long. Maximum: {max_duration}s"

        return True, ""

    except FileNotFoundError:
        return False, "Audio file not found"
    except ValueError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Audio validation error: {str(e)}"
