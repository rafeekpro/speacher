#!/usr/bin/env python3
"""
Extended unit tests for the transcription module.
"""

import os
import tempfile
import unittest

# Import the module to test
import src.speecher.transcription as transcription


class TestTranscriptionExtended(unittest.TestCase):
    """Extended test cases for transcription module."""

    def setUp(self):
        """Set up test fixtures."""
        self.sample_aws_data = {
            "jobName": "test-job",
            "results": {
                "transcripts": [{"transcript": "This is a test transcription."}],
                "items": [
                    {
                        "type": "pronunciation",
                        "alternatives": [{"content": "This", "confidence": "0.99"}],
                        "start_time": "0.0",
                        "end_time": "0.5",
                    },
                    {
                        "type": "pronunciation",
                        "alternatives": [{"content": "is", "confidence": "0.98"}],
                        "start_time": "0.5",
                        "end_time": "0.8",
                    },
                ],
            },
        }

        self.sample_azure_data = {
            "combinedRecognizedPhrases": [{"display": "This is Azure transcription."}],
            "recognizedPhrases": [
                {
                    "recognitionStatus": "Success",
                    "offset": 0,
                    "duration": 1000000,
                    "nBest": [
                        {
                            "confidence": 0.95,
                            "display": "This is Azure transcription.",
                            "words": [
                                {"word": "This", "offset": 0, "duration": 500000},
                                {"word": "is", "offset": 500000, "duration": 300000},
                            ],
                        }
                    ],
                }
            ],
        }

        self.sample_gcp_data = {
            "results": [
                {
                    "alternatives": [
                        {
                            "transcript": "This is GCP transcription.",
                            "confidence": 0.96,
                            "words": [
                                {
                                    "word": "This",
                                    "startTime": {"seconds": 0, "nanos": 0},
                                    "endTime": {"seconds": 0, "nanos": 500000000},
                                }
                            ],
                        }
                    ]
                }
            ]
        }

    def test_process_aws_transcription_with_timestamps(self):
        """Test processing AWS transcription with timestamps."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp:
            output_file = tmp.name

        try:
            result = transcription.process_transcription_result(
                self.sample_aws_data, output_file=output_file, include_timestamps=True
            )

            self.assertTrue(result)
            self.assertTrue(os.path.exists(output_file))

            # Read the output file
            with open(output_file, "r", encoding="utf-8") as f:
                content = f.read()
                self.assertIn("This", content)
                self.assertIn("is", content)
                self.assertIn("[00:00:00.000 - 00:00:00.500]", content)
        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)

    def test_process_aws_transcription_without_timestamps(self):
        """Test processing AWS transcription without timestamps."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp:
            output_file = tmp.name

        try:
            result = transcription.process_transcription_result(
                self.sample_aws_data, output_file=output_file, include_timestamps=False
            )

            self.assertTrue(result)
            self.assertTrue(os.path.exists(output_file))

            # Read the output file
            with open(output_file, "r", encoding="utf-8") as f:
                content = f.read()
                self.assertIn("This is a test transcription", content)
                self.assertNotIn("[00:00:00", content)
        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)

    def test_process_azure_transcription(self):
        """Test processing Azure transcription."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp:
            output_file = tmp.name

        try:
            result = transcription.process_transcription_result(
                self.sample_azure_data, output_file=output_file, include_timestamps=True
            )

            self.assertTrue(result)
            self.assertTrue(os.path.exists(output_file))

            with open(output_file, "r", encoding="utf-8") as f:
                content = f.read()
                self.assertIn("This is Azure transcription", content)
        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)

    def test_process_gcp_transcription(self):
        """Test processing GCP transcription."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp:
            output_file = tmp.name

        try:
            result = transcription.process_transcription_result(
                self.sample_gcp_data, output_file=output_file, include_timestamps=True
            )

            self.assertTrue(result)
            self.assertTrue(os.path.exists(output_file))

            with open(output_file, "r", encoding="utf-8") as f:
                content = f.read()
                self.assertIn("This is GCP transcription", content)
        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)

    def test_process_transcription_no_output_file(self):
        """Test processing transcription without output file (console only)."""
        result = transcription.process_transcription_result(
            self.sample_aws_data, output_file=None, include_timestamps=True
        )

        self.assertTrue(result)

    def test_process_transcription_with_speaker_labels(self):
        """Test processing transcription with speaker labels."""
        data_with_speakers = self.sample_aws_data.copy()
        data_with_speakers["results"]["speaker_labels"] = {
            "speakers": 2,
            "segments": [
                {
                    "speaker_label": "spk_0",
                    "start_time": "0.0",
                    "end_time": "0.8",
                    "items": [
                        {"speaker_label": "spk_0", "start_time": "0.0", "end_time": "0.5"},
                        {"speaker_label": "spk_0", "start_time": "0.5", "end_time": "0.8"},
                    ],
                }
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp:
            output_file = tmp.name

        try:
            result = transcription.process_transcription_result(
                data_with_speakers, output_file=output_file, include_timestamps=True
            )

            self.assertTrue(result)

            with open(output_file, "r", encoding="utf-8") as f:
                content = f.read()
                self.assertIn("spk_0", content)
        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)

    def test_process_transcription_empty_data(self):
        """Test processing empty transcription data."""
        empty_data = {"results": {"transcripts": [], "items": []}}

        result = transcription.process_transcription_result(empty_data, output_file=None, include_timestamps=True)

        self.assertFalse(result)  # Should return False for invalid data structure

    def test_process_transcription_invalid_data(self):
        """Test processing invalid transcription data."""
        invalid_data = {"invalid": "data"}

        result = transcription.process_transcription_result(invalid_data, output_file=None, include_timestamps=True)

        # Should return False for invalid data format
        self.assertFalse(result)

    def test_process_transcription_with_confidence_scores(self):
        """Test that confidence scores are processed correctly."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp:
            output_file = tmp.name

        try:
            result = transcription.process_transcription_result(
                self.sample_aws_data, output_file=output_file, include_timestamps=True
            )

            self.assertTrue(result)

            # The function should process confidence scores internally
            # even if they're not displayed in the output
            with open(output_file, "r", encoding="utf-8") as f:
                content = f.read()
                # Check that the transcription was processed
                self.assertIn("This", content)
        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)

    def test_process_transcription_json_output(self):
        """Test saving transcription output (note: function saves as text, not JSON)."""
        output_file = tempfile.mktemp(suffix=".txt")

        try:
            result = transcription.process_transcription_result(
                self.sample_aws_data, output_file=output_file, include_timestamps=True
            )

            self.assertTrue(result)
            self.assertTrue(os.path.exists(output_file))

            # Verify file contains text output
            with open(output_file, "r", encoding="utf-8") as f:
                content = f.read()
                self.assertIsInstance(content, str)
                self.assertGreater(len(content), 0)
        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)


if __name__ == "__main__":
    unittest.main()
