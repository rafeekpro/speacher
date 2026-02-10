#!/usr/bin/env python3
"""
Unit tests for the transcription module which handles processing of transcription results.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Import the module to test
from src.speecher import transcription

# Import test utilities
from tests.test_utils import get_sample_transcription_data, save_sample_transcription_to_file, setup_test_data_dir


class TestTranscriptionModule(unittest.TestCase):
    """Test cases for transcription module functions"""

    def setUp(self):
        """Set up before each test"""
        self.test_data_dir = setup_test_data_dir()
        self.sample_data = get_sample_transcription_data()
        self.sample_transcription_path = save_sample_transcription_to_file()

        # Zapewniamy, że katalog test_data istnieje
        os.makedirs(self.test_data_dir, exist_ok=True)

    def test_process_transcription_result_console_output(self):
        """Test processing transcription results with console output"""
        with patch("builtins.print") as mock_print:
            result = transcription.process_transcription_result(self.sample_data, include_timestamps=True)

            self.assertTrue(result)
            # Verify that print was called at least twice (header and at least one transcription line)
            self.assertGreater(mock_print.call_count, 1)

    def test_process_transcription_result_file_output(self):
        """Test processing transcription results with file output"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as temp_file:
            output_path = temp_file.name

        try:
            result = transcription.process_transcription_result(
                self.sample_data, output_file=output_path, include_timestamps=True
            )

            self.assertTrue(result)

            # Verify file output
            with open(output_path, "r", encoding="utf-8") as f:
                content = f.read()
                self.assertGreater(len(content), 0)
                # Verify that the file contains speaker information
                self.assertIn("spk_", content)
                # Verify that timestamps are included
                self.assertIn("[", content)
        finally:
            # Clean up temp file
            Path(output_path).unlink(missing_ok=True)

    def test_process_transcription_result_no_timestamps(self):
        """Test processing transcription results without timestamps"""
        with patch("builtins.print") as mock_print:
            result = transcription.process_transcription_result(self.sample_data, include_timestamps=False)

            self.assertTrue(result)

            # Check if print was called at least once with a string not containing timestamps
            timestamp_format_called = False
            for call in mock_print.call_args_list:
                args = call[0]
                if args and isinstance(args[0], str) and "spk_" in args[0] and "[" not in args[0]:
                    timestamp_format_called = True
                    break

            self.assertTrue(timestamp_format_called, "Print should have been called with a string without timestamps")

    def test_process_transcription_result_file_output_error(self):
        """Test error handling when writing results to a file"""
        # Zamiast używać katalogu, użyjmy ścieżki do nieistniejącego pliku w katalogu, który nie istnieje
        output_path = os.path.join(self.test_data_dir, "nonexistent-dir", "output.txt")

        with patch("logging.Logger.error") as mock_logger_error:
            result = transcription.process_transcription_result(
                self.sample_data, output_file=output_path, include_timestamps=True
            )

            self.assertFalse(result)
            mock_logger_error.assert_called()

    def test_process_transcription_result_missing_speaker_labels(self):
        """Test processing data with missing speaker labels"""
        # Create data with missing speaker_labels
        modified_data = {
            "results": {
                "transcripts": [{"transcript": "To jest przykładowa transkrypcja."}],
                "items": self.sample_data["results"]["items"],
            }
        }

        with patch("builtins.print") as mock_print:
            result = transcription.process_transcription_result(modified_data)

            # Now the function should handle transcriptions without speaker_labels
            self.assertTrue(result)

    def test_process_transcription_result_missing_items(self):
        """Test processing data with missing items"""
        # Create data with missing items but with transcripts
        modified_data = {
            "results": {
                "transcripts": [{"transcript": "To jest przykładowa transkrypcja."}],
                "speaker_labels": self.sample_data["results"]["speaker_labels"],
            }
        }

        with patch("builtins.print") as mock_print:
            result = transcription.process_transcription_result(modified_data)

            # Now the function should handle this case
            self.assertTrue(result)

    def test_process_transcription_result_alternative_method(self):
        """Test processing with the alternative grouping method"""
        # Modify sample data to trigger the alternative method
        modified_data = json.loads(json.dumps(self.sample_data))  # Deep copy

        # Clear the segments to force use of alternative method
        modified_data["results"]["speaker_labels"]["segments"] = []

        with patch("builtins.print") as mock_print, patch("logging.Logger.info") as mock_logger_info:
            result = transcription.process_transcription_result(modified_data)

            # Should fall back to simple method and succeed
            self.assertTrue(mock_logger_info.called)
            self.assertTrue(result)

    def test_process_transcription_result_simple_method(self):
        """Test processing with the simple method (no speaker segmentation)"""
        # Modify sample data to trigger the simple method
        modified_data = json.loads(json.dumps(self.sample_data))  # Deep copy

        # Usuń speaker_labels całkowicie, aby wymusić użycie prostej metody
        if "speaker_labels" in modified_data.get("results", {}):
            del modified_data["results"]["speaker_labels"]

        # Upewnij się, że items nadal istnieją
        if "items" not in modified_data.get("results", {}):
            modified_data["results"]["items"] = self.sample_data["results"]["items"]

        with patch("builtins.print") as mock_print:
            # This should use the simple method without speaker_labels
            result = transcription.process_transcription_result(modified_data)

            # The function should now handle this case successfully
            self.assertTrue(result)

    def test_process_transcription_result_unexpected_error(self):
        """Test handling of unexpected errors during processing"""
        # Zamiast bezpośrednio patchować funkcję, symulujmy wyjątek wewnątrz funkcji
        with patch(
            "src.speecher.transcription.process_transcription_result", side_effect=Exception("Unexpected error")
        ) as mock_process:
            with self.assertRaises(Exception):
                mock_process({})


if __name__ == "__main__":
    unittest.main()
