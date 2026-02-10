#!/usr/bin/env python3
"""
Skrypt pomocniczy do uruchamiania testów i zapisywania wyników do pliku.
"""

import os
import sys
import unittest
import datetime
from pathlib import Path

def run_tests_and_save_results():
    """Uruchom testy i zapisz wyniki do pliku"""
    # Utwórz katalog na wyniki testów, jeśli nie istnieje
    results_dir = Path(__file__).parent / "test_results"
    results_dir.mkdir(exist_ok=True)
    
    # Nazwa pliku z wynikami testów zawierająca aktualną datę i czas
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = results_dir / f"test_results_{timestamp}.txt"
    
    # Przekieruj standardowe wyjście do pliku
    original_stdout = sys.stdout
    with open(results_file, 'w') as f:
        sys.stdout = f
        
        # Wykryj i uruchom wszystkie testy
        print(f"=== Wyniki testów dla projektu Speecher - {datetime.datetime.now()} ===\n")
        
        # Zapisz informacje o środowisku
        print(f"Python: {sys.version}")
        print(f"Katalog roboczy: {os.getcwd()}")
        print()
        
        # Uruchom testy
        suite = unittest.defaultTestLoader.discover('tests')
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        
        # Wypisz podsumowanie wyników
        print("\n=== Podsumowanie ===")
        print(f"Uruchomiono: {result.testsRun}")
        print(f"Błędy: {len(result.errors)}")
        print(f"Niepowodzenia: {len(result.failures)}")
        print(f"Pominięto: {len(result.skipped)}")
        
        # Przywróć standardowe wyjście
        sys.stdout = original_stdout
    
    print(f"Wyniki testów zostały zapisane do: {results_file}")
    
    # Wyświetl wyniki testów
    with open(results_file, 'r') as f:
        print("\n=== WYNIKI TESTÓW ===")
        print(f.read())
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_tests_and_save_results()
    sys.exit(0 if success else 1)