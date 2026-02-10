#!/usr/bin/env python3
"""
Skrypt do uruchamiania testów i zapisywania wyników do pliku
"""

import unittest
import sys
import os
import tempfile
from datetime import datetime
from pathlib import Path


def run_tests():
    """Uruchom testy i zapisz wyniki do pliku"""
    # Ścieżka do pliku wynikowego
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"test_output_{timestamp}.txt"
    
    # Utwórz tymczasowy plik z wynikami testów
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp_file:
        # Przekieruj stdout do pliku tymczasowego
        original_stdout = sys.stdout
        sys.stdout = tmp_file
        
        # Pobierz katalog tests
        tests_dir = Path(__file__).parent / "tests"
        print(f"Uruchamiam testy z katalogu: {tests_dir}")

        # Upewnij się, że katalog test_data istnieje
        test_data_dir = tests_dir / "test_data"
        os.makedirs(test_data_dir, exist_ok=True)
        print(f"Katalog test_data: {test_data_dir}")
        
        # Uruchom testy
        loader = unittest.TestLoader()
        suite = loader.discover(str(tests_dir))
        
        # Utwórz runner, który będzie zbierał wyniki
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        
        # Wypisz szczegółowe informacje o błędach
        if result.errors:
            print("\n==== ERRORS ====")
            for test, error in result.errors:
                print(f"\n--- {test} ---")
                print(error)
        
        if result.failures:
            print("\n==== FAILURES ====")
            for test, failure in result.failures:
                print(f"\n--- {test} ---")
                print(failure)
        
        # Wypisz podsumowanie
        test_count = result.testsRun
        print(f"\n==== PODSUMOWANIE ====")
        print(f"Uruchomiono: {test_count} testów")
        print(f"Błędy: {len(result.errors)}")
        print(f"Niepowodzenia: {len(result.failures)}")
        print(f"Pominięte: {len(result.skipped)}")
        
        # Przywróć standardowe wyjście
        sys.stdout = original_stdout
    
    # Kopiuj dane z pliku tymczasowego do pliku wynikowego
    with open(tmp_file.name, 'r') as src, open(output_file, 'w') as dst:
        dst.write(src.read())
    
    # Usuń plik tymczasowy
    os.unlink(tmp_file.name)
    
    print(f"Wyniki testów zostały zapisane do pliku: {output_file}")
    
    # Otwórz i wypisz zawartość pliku wynikowego
    with open(output_file, 'r') as f:
        file_content = f.read()
        print("Zawartość pliku wynikowego:")
        print(file_content)
    
    return result.wasSuccessful(), output_file


if __name__ == "__main__":
    print("\n==== URUCHAMIAM TESTY DLA APLIKACJI SPEECHER ====\n")
    success, output_file = run_tests()
    
    print(f"Wyniki testów zostały zapisane do pliku: {output_file}")
    print(f"Status testów: {'SUKCES' if success else 'BŁĄD'}")
    
    # Ustaw kod wyjścia
    if not success:
        sys.exit(1)
    
    sys.exit(0)