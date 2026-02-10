#!/usr/bin/env python3
"""Test the backend with a mock transcription result"""

import requests
import json

# Test endpoint with mock data
url = "http://localhost:8000/transcribe"

# Create a simple test file
test_content = b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00D\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00"

files = {"file": ("test.wav", test_content, "audio/wav")}
data = {
    "provider": "aws",
    "language": "en-US",
    "enable_diarization": False,
    "max_speakers": 1,
    "include_timestamps": False
}

print("Testing /transcribe endpoint with minimal request")
print(f"Request data: {data}")

try:
    response = requests.post(url, files=files, data=data)
    print(f"Response status: {response.status_code}")
    
    if response.status_code == 200:
        print("Success!")
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"Error: {response.status_code}")
        print(f"Response: {response.text}")
        
except Exception as e:
    print(f"Request failed: {e}")