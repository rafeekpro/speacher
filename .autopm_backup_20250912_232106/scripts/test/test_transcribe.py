#!/usr/bin/env python3
"""Test script for the /transcribe endpoint"""

import requests
import sys
from pathlib import Path

# Use test WAV file (longer duration for AWS requirements)
test_file = "/tmp/test_audio_long.wav"

# Check if test file exists, create a minimal one if not
if not Path(test_file).exists():
    print(f"Test file {test_file} does not exist")
    print("Please provide a valid WAV file path as an argument")
    sys.exit(1)

# Prepare the request
url = "http://localhost:8000/transcribe"
files = {"file": open(test_file, "rb")}
data = {
    "provider": "aws",
    "language": "en-US",
    "enable_diarization": True,
    "max_speakers": 4,
    "include_timestamps": True
}

print(f"Testing /transcribe endpoint with file: {test_file}")
print(f"Request data: {data}")

try:
    response = requests.post(url, files=files, data=data)
    print(f"Response status: {response.status_code}")
    
    if response.status_code == 200:
        print("Success! Transcription result:")
        print(response.json())
    else:
        print(f"Error: {response.status_code}")
        print(f"Response: {response.text}")
        
except Exception as e:
    print(f"Request failed: {e}")