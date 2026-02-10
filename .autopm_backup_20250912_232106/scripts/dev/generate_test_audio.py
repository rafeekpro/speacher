#!/usr/bin/env python3
"""Generate a test audio file of sufficient length for AWS Transcribe"""

import wave
import struct
import math
import os

def generate_sine_wave(frequency=440, duration=1.0, sample_rate=44100, amplitude=0.5):
    """Generate a sine wave"""
    num_samples = int(sample_rate * duration)
    samples = []
    
    for i in range(num_samples):
        t = float(i) / sample_rate
        value = amplitude * math.sin(2 * math.pi * frequency * t)
        # Convert to 16-bit PCM
        packed_value = struct.pack('h', int(value * 32767))
        samples.append(packed_value)
    
    return b''.join(samples)

def create_test_wav(filename, duration=1.0):
    """Create a test WAV file with sine wave audio"""
    sample_rate = 44100
    nchannels = 1  # Mono
    sampwidth = 2   # 16-bit
    
    # Generate audio data
    audio_data = generate_sine_wave(duration=duration, sample_rate=sample_rate)
    
    # Write WAV file
    with wave.open(filename, 'wb') as wav_file:
        wav_file.setnchannels(nchannels)
        wav_file.setsampwidth(sampwidth)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_data)
    
    print(f"Created test WAV file: {filename}")
    print(f"Duration: {duration} seconds")
    print(f"Size: {os.path.getsize(filename)} bytes")

if __name__ == "__main__":
    # Create a 1-second test audio file (minimum 0.5s required by AWS)
    output_file = "/tmp/test_audio_long.wav"
    create_test_wav(output_file, duration=1.0)
    print(f"\nTest audio file created at: {output_file}")
    print("This file can be used for testing the transcription endpoint")