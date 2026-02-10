#!/usr/bin/env python3
"""
AWS Audio Transcriber

Program do transkrypcji plików audio .wav z wykorzystaniem usług AWS.
Wykorzystuje Amazon S3 do przechowywania plików oraz Amazon Transcribe do transkrypcji.
"""

import argparse
import logging
import uuid
from pathlib import Path

from . import aws, transcription

# Konfiguracja logowania
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main():
    """Główna funkcja programu."""
    parser = argparse.ArgumentParser(description="Transkrypcja pliku audio .wav z użyciem AWS Transcribe")
    parser.add_argument("--audio-file", default="audio.wav", help="Ścieżka do pliku audio .wav (domyślnie: audio.wav)")
    parser.add_argument("--keep-resources", action="store_true", help="Nie usuwaj zasobów AWS po zakończeniu")
    parser.add_argument("--region", help="Region AWS (domyślnie: region z konfiguracji AWS)")
    parser.add_argument("--bucket-name", help="Użyj istniejącego bucketu S3 zamiast tworzenia nowego")
    parser.add_argument(
        "--language", default="pl-PL", help="Kod języka do transkrypcji (domyślnie: pl-PL, np. es-ES dla hiszpańskiego)"
    )
    parser.add_argument(
        "--max-speakers", type=int, default=5, help="Maksymalna liczba mówców do identyfikacji (domyślnie: 5)"
    )
    parser.add_argument("--output-file", help="Ścieżka do pliku wyjściowego, gdzie zostanie zapisana transkrypcja")
    parser.add_argument(
        "--include-timestamps",
        action="store_true",
        default=True,
        help="Czy dołączać znaczniki czasu do transkrypcji (domyślnie: włączone)",
    )
    parser.add_argument("--no-timestamps", action="store_true", help="Wyłącz znaczniki czasu w transkrypcji")
    parser.add_argument("--audio-length", type=float, help="Długość pliku audio w sekundach (do oszacowania kosztów)")
    parser.add_argument("--show-cost", action="store_true", help="Pokaż szacunkowy koszt usługi")
    args = parser.parse_args()

    # Jeśli podano flagę --no-timestamps, wyłącz znaczniki czasu
    if args.no_timestamps:
        args.include_timestamps = False

    # Sprawdź, czy podany kod języka jest prawidłowy
    supported_languages = aws.get_supported_languages()

    if args.language not in supported_languages:
        logger.warning(f"Uwaga: Podany kod języka '{args.language}' może nie być obsługiwany przez AWS Transcribe.")
        logger.info(f"Popularne kody języków: {', '.join(supported_languages.keys())}")
    else:
        logger.info(f"Używam języka: {supported_languages[args.language]} ({args.language})")

    audio_path = Path(args.audio_file)

    # Sprawdź, czy plik istnieje
    if not audio_path.exists():
        logger.error(f"Plik {audio_path} nie istnieje")
        return 1

    # Sprawdź, czy plik ma rozszerzenie .wav
    if audio_path.suffix.lower() != ".wav":
        logger.error(f"Plik {audio_path} nie jest plikiem .wav")
        return 1

    # Spróbuj określić długość audio
    audio_length_seconds = args.audio_length
    if args.show_cost and audio_length_seconds is None:
        try:
            # Próba określenia długości pliku audio - wymaga zainstalowania biblioteki pydub
            try:
                from pydub import AudioSegment

                audio = AudioSegment.from_file(str(audio_path))
                audio_length_seconds = len(audio) / 1000.0  # długość w sekundach
                logger.info(f"Określono długość pliku audio: {audio_length_seconds:.2f} sekund")
            except ImportError:
                logger.warning(
                    "Nie można określić długości pliku audio - zainstaluj bibliotekę pydub używając komendy: poetry add pydub"
                )
                # Ustawmy domyślną długość pliku, aby pokazać przykładowe koszty
                audio_length_seconds = 300.0  # Załóżmy 5 minut jako domyślną długość
                logger.warning(
                    f"Używam domyślnej długości pliku audio: {audio_length_seconds:.2f} sekund. Użyj parametru --audio-length, aby podać dokładną długość."
                )
        except Exception as e:
            logger.warning(f"Nie można określić długości pliku audio: {e}")
            # Ustawmy domyślną długość pliku, aby pokazać przykładowe koszty
            audio_length_seconds = 300.0  # Załóżmy 5 minut jako domyślną długość
            logger.warning(
                f"Używam domyślnej długości pliku audio: {audio_length_seconds:.2f} sekund. Użyj parametru --audio-length, aby podać dokładną długość."
            )

    try:
        # 1. Użyj istniejącego bucketu lub utwórz nowy
        bucket_name = None
        need_cleanup = False  # Flaga informująca, czy należy usunąć bucket po zakończeniu

        if args.bucket_name:
            bucket_name = args.bucket_name
            logger.info(f"Używam istniejącego bucketu S3: {bucket_name}")
        else:
            bucket_name = aws.create_unique_bucket_name()
            if not aws.create_s3_bucket(bucket_name, region=args.region):
                return 1
            need_cleanup = True  # Tylko jeśli sami tworzymy bucket, powinniśmy go usunąć

        # 2. Wgraj plik audio do S3
        audio_filename = audio_path.name
        if not aws.upload_file_to_s3(str(audio_path), bucket_name, audio_filename):
            return 1

        # 3. Utwórz i uruchom zadanie transkrypcji
        job_name = f"transcription-{uuid.uuid4()}"
        transcription_response = aws.start_transcription_job(
            job_name, bucket_name, audio_filename, language_code=args.language, max_speakers=args.max_speakers
        )

        if not transcription_response:
            return 1

        # 4. Poczekaj na zakończenie zadania
        job_info = aws.wait_for_job_completion(job_name)
        if not job_info:
            return 1

        # 5. Pobierz wynik transkrypcji
        transcript_url = job_info["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]
        transcription_data = aws.download_transcription_result(transcript_url)
        if not transcription_data:
            return 1

        # 6. Przetwórz i wyświetl wynik
        if not transcription.process_transcription_result(
            transcription_data, output_file=args.output_file, include_timestamps=args.include_timestamps
        ):
            return 1

        # 7. Opcjonalnie wyczyść zasoby tylko jeśli sami je stworzyliśmy
        if need_cleanup and not args.keep_resources:
            aws.cleanup_resources(bucket_name)
        elif need_cleanup and args.keep_resources:
            logger.info(f"Zasoby nie zostały usunięte. Bucket S3: {bucket_name}, Zadanie transkrypcji: {job_name}")
        else:
            # Usuwamy tylko plik, nie usuwamy istniejącego bucketu
            aws.delete_file_from_s3(bucket_name, audio_filename)
            logger.info(f"Usunięto plik {audio_filename} z bucketu {bucket_name}")

        # 8. Wyświetl informacje o koszcie usługi
        if args.show_cost:
            cost_info = aws.calculate_service_cost(audio_length_seconds, args.language)

            print("\n=== INFORMACJE O KOSZTACH TRANSKRYPCJI ===\n")
            print(f"Długość audio: {audio_length_seconds:.2f} sekund ({audio_length_seconds/60:.2f} minut)")
            print(f"Szacunkowy rozmiar pliku: {cost_info['audio_size_mb']:.2f} MB")
            print(f"\nKoszt transkrypcji: ${cost_info['transcribe_cost']:.4f} USD")
            print(f"Koszt przechowywania S3: ${cost_info['s3_storage_cost']:.6f} USD/dzień")
            print(f"Koszt żądań S3: ${cost_info['s3_request_cost']:.6f} USD")
            print(f"\nSZACUNKOWY CAŁKOWITY KOSZT: ${cost_info['total_cost']:.4f} USD")

            if args.audio_length is None and not audio_length_seconds:
                print("\nUWAGA: Koszt jest szacowany na podstawie domyślnej długości pliku audio (5 minut).")
                print("Aby uzyskać dokładniejsze szacunki, użyj parametru --audio-length.")

        return 0

    except Exception as e:
        logger.error(f"Wystąpił nieoczekiwany błąd: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
