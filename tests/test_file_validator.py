"""Tests for file validation utilities"""

from src.backend.file_validator import (
    AudioFormat,
    detect_audio_format,
    get_audio_duration_estimate,
    validate_audio_file,
)


class TestFileValidator:
    """Test suite for file validation"""

    def test_detect_wav_format(self):
        """Test WAV format detection"""
        # Valid WAV header
        wav_header = b"RIFF\x00\x00\x00\x00WAVE"
        assert detect_audio_format(wav_header) == AudioFormat.WAV

    def test_detect_mp3_format(self):
        """Test MP3 format detection"""
        # MP3 with ID3 tag (needs at least 12 bytes)
        mp3_id3 = b"ID3\x03\x00\x00\x00\x00\x00\x00\x00\x00"
        assert detect_audio_format(mp3_id3) == AudioFormat.MP3

        # MP3 without ID3 (needs at least 12 bytes)
        mp3_raw = b"\xff\xfb\x90\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        assert detect_audio_format(mp3_raw) == AudioFormat.MP3

    def test_detect_flac_format(self):
        """Test FLAC format detection"""
        flac_header = b"fLaC\x00\x00\x00\x22\x00\x00\x00\x00"
        assert detect_audio_format(flac_header) == AudioFormat.FLAC

    def test_detect_ogg_format(self):
        """Test OGG format detection"""
        ogg_header = b"OggS\x00\x02\x00\x00\x00\x00\x00\x00"
        assert detect_audio_format(ogg_header) == AudioFormat.OGG

    def test_detect_m4a_format(self):
        """Test M4A format detection"""
        m4a_header = b"\x00\x00\x00\x20ftypM4A \x00\x00\x00\x00"
        assert detect_audio_format(m4a_header) == AudioFormat.M4A

    def test_detect_unknown_format(self):
        """Test unknown format detection"""
        unknown = b"UNKNOWN_FORMAT"
        assert detect_audio_format(unknown) is None

        # Empty file
        assert detect_audio_format(b"") is None

        # Too small file
        assert detect_audio_format(b"ABC") is None

    def test_validate_valid_wav_file(self):
        """Test validation of valid WAV file"""
        wav_content = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00"
        is_valid, message, format = validate_audio_file(wav_content, "test.wav")

        assert is_valid is True
        assert "Valid WAV" in message
        assert format == AudioFormat.WAV

    def test_validate_empty_file(self):
        """Test validation of empty file"""
        is_valid, message, format = validate_audio_file(b"", "empty.wav")

        assert is_valid is False
        assert "empty" in message.lower()
        assert format is None

    def test_validate_file_too_large(self):
        """Test validation of file exceeding size limit"""
        large_content = b"RIFF" + b"0" * (10 * 1024 * 1024)  # 10MB
        is_valid, message, format = validate_audio_file(
            large_content, "large.wav", max_size=5 * 1024 * 1024  # 5MB limit
        )

        assert is_valid is False
        assert "too large" in message.lower()

    def test_validate_corrupted_file(self):
        """Test validation of corrupted file"""
        corrupted = b"CORRUPTED_FILE_CONTENT"
        is_valid, message, format = validate_audio_file(corrupted, "corrupted.wav")

        assert is_valid is False
        assert "corrupted" in message.lower()

    def test_validate_test_file_allowed(self):
        """Test validation with test files allowed"""
        test_content = b"test_audio_data"
        is_valid, message, format = validate_audio_file(test_content, "test.wav", allow_test_files=True)

        assert is_valid is True
        assert "test" in message.lower()

    def test_validate_test_file_not_allowed(self):
        """Test validation with test files not allowed"""
        test_content = b"test_audio_data"
        is_valid, message, format = validate_audio_file(test_content, "test.wav", allow_test_files=False)

        assert is_valid is False

    def test_validate_mock_file(self):
        """Test validation of mock file"""
        mock_content = b"mock_audio_content"
        is_valid, message, format = validate_audio_file(mock_content, "mock.wav", allow_test_files=True)

        assert is_valid is True
        assert "test" in message.lower()

    def test_unsupported_format(self):
        """Test validation of unsupported format"""
        unsupported = b"UNSUPPORTED"
        is_valid, message, format = validate_audio_file(unsupported, "file.xyz")

        assert is_valid is False
        assert "unsupported" in message.lower()

    def test_duration_estimate_wav(self):
        """Test duration estimation for WAV"""
        # 172KB/s for typical WAV
        wav_content = b"X" * (172 * 1024 * 10)  # 10 seconds worth
        duration = get_audio_duration_estimate(wav_content, AudioFormat.WAV)

        assert duration is not None
        assert 9 < duration < 11  # Should be around 10 seconds

    def test_duration_estimate_mp3(self):
        """Test duration estimation for MP3"""
        # 16KB/s for 128kbps MP3
        mp3_content = b"X" * (16 * 1024 * 10)  # 10 seconds worth
        duration = get_audio_duration_estimate(mp3_content, AudioFormat.MP3)

        assert duration is not None
        assert 9 < duration < 11  # Should be around 10 seconds
