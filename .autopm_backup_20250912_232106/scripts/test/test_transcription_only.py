#!/usr/bin/env python3
"""
Uproszczony skrypt testowy dla modułu transcription.py
"""

import unittest
from pathlib import Path

# Import testów
from tests.test_transcription import TestTranscriptionModule

if __name__ == "__main__":
    # Utwórz katalog na wyniki, jeśli nie istnieje
    results_dir = Path(__file__).parent / "test_results"
    results_dir.mkdir(exist_ok=True)
    
    # Plik wynikowy
    results_file = results_dir / "transcription_test_results.txt"
    
    # Uruchom testy i zapisz wyniki
    with open(results_file, 'w') as f:
        suite = unittest.TestLoader().loadTestsFromTestCase(TestTranscriptionModule)
        unittest.TextTestRunner(stream=f, verbosity=2).run(suite)
    
    # Wyświetl wyniki
    print(f"Zapisano wyniki testów do: {results_file}")
    
    # Wyświetl zawartość pliku wynikowego
    with open(results_file, 'r') as f:
        print("\n--- WYNIKI TESTÓW ---")
        print(f.read())