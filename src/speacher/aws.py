#!/usr/bin/env python3
"""
AWS Service Module

Moduł zawierający funkcje do interakcji z usługami AWS:
- Amazon S3 do przechowywania plików audio
- Amazon Transcribe do transkrypcji mowy na tekst
"""

import logging
import os
import time
import uuid

import boto3
import requests
from botocore.exceptions import ClientError

# Konfiguracja loggera
logger = logging.getLogger(__name__)


def create_unique_bucket_name(base_name="audio-transcription"):
    """Tworzy unikalną nazwę dla bucketu S3."""
    # Dodajemy losowy UUID do nazwy aby była unikalna
    unique_id = str(uuid.uuid4())[:8]
    return f"{base_name}-{unique_id}"


def create_s3_bucket(bucket_name, region=None):
    """
    Tworzy bucket S3 z podaną nazwą.

    Args:
        bucket_name: Nazwa dla nowego bucketu
        region: Region AWS, domyślnie używa regionu z konfiguracji

    Returns:
        str|None: Nazwa utworzonego bucketu lub None w przypadku błędu
    """
    try:
        s3_client = boto3.client("s3", region_name=region)
        if region is None:
            region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

        # Sprawdź czy bucket już istnieje
        try:
            s3_client.head_bucket(Bucket=bucket_name)
            logger.info(f"Bucket {bucket_name} już istnieje")
            return bucket_name
        except ClientError as e:
            if e.response["Error"]["Code"] != "404":
                logger.error(f"Błąd podczas sprawdzania bucketu: {e}")
                return None

        # Jeśli bucket już istnieje ale należy do kogoś innego, spróbuj z unikalną nazwą
        original_bucket_name = bucket_name
        attempts = 0
        max_attempts = 5

        while attempts < max_attempts:
            try:
                # Tworzymy bucket - dla regionów innych niż us-east-1 musimy podać LocationConstraint
                if region == "us-east-1":
                    response = s3_client.create_bucket(Bucket=bucket_name)
                else:
                    response = s3_client.create_bucket(
                        Bucket=bucket_name, CreateBucketConfiguration={"LocationConstraint": region}
                    )
                logger.info(f"Bucket {bucket_name} został utworzony w regionie {region}")
                return bucket_name
            except ClientError as e:
                error_code = e.response["Error"]["Code"]
                if error_code in ["BucketAlreadyExists", "BucketAlreadyOwnedByYou"]:
                    attempts += 1
                    # Dodaj losowy suffix do nazwy
                    unique_suffix = str(uuid.uuid4())[:8]
                    bucket_name = f"{original_bucket_name}-{unique_suffix}"
                    logger.info(f"Bucket name taken, trying: {bucket_name}")
                else:
                    logger.error(f"Błąd podczas tworzenia bucketu: {e}")
                    return None

        logger.error(f"Nie udało się utworzyć bucketu po {max_attempts} próbach")
        return None
    except ClientError as e:
        logger.error(f"Błąd podczas tworzenia bucketu: {e}")
        return None


def upload_file_to_s3(file_path, bucket_name, object_name=None):
    """
    Wgrywa plik do bucketu S3.

    Args:
        file_path: Ścieżka do pliku lokalnego
        bucket_name: Nazwa bucketu S3
        object_name: Nazwa obiektu w S3 (jeśli None, używa nazwy pliku)

    Returns:
        tuple: (bool, str) - (success, actual_bucket_name) or (False, None) w przypadku błędu
    """
    if object_name is None:
        object_name = os.path.basename(file_path)

    try:
        s3_client = boto3.client("s3")

        # Check if bucket exists, create if it doesn't
        try:
            s3_client.head_bucket(Bucket=bucket_name)
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "404":
                logger.info(f"Bucket {bucket_name} doesn't exist, creating it...")
                created_bucket_name = create_s3_bucket(bucket_name)
                if not created_bucket_name:
                    logger.error(f"Failed to create bucket {bucket_name}")
                    return (False, None)
                # Update bucket name if it was changed during creation
                bucket_name = created_bucket_name
            else:
                raise e

        s3_client.upload_file(file_path, bucket_name, object_name)
        logger.info(f"Plik {file_path} został wgrany do bucketu {bucket_name} jako {object_name}")
        return (True, bucket_name)
    except ClientError as e:
        logger.error(f"Błąd podczas wgrywania pliku: {e}")
        return (False, None)


def start_transcription_job(job_name, bucket_name, object_key, language_code="pl-PL", max_speakers=5):
    """
    Uruchamia zadanie transkrypcji audio w Amazon Transcribe.

    Args:
        job_name: Unikalna nazwa zadania transkrypcji
        bucket_name: Nazwa bucketu S3 z plikiem audio
        object_key: Nazwa pliku w S3
        language_code: Kod języka (default: pl-PL)
        max_speakers: Maksymalna liczba mówców do identyfikacji

    Returns:
        dict: Odpowiedź z Amazon Transcribe lub None w przypadku błędu
    """
    try:
        transcribe_client = boto3.client("transcribe")

        # Format MediaFileUri: s3://bucket-name/object-key
        media_uri = f"s3://{bucket_name}/{object_key}"

        response = transcribe_client.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={"MediaFileUri": media_uri},
            MediaFormat="wav",
            LanguageCode=language_code,
            Settings={"ShowSpeakerLabels": True, "MaxSpeakerLabels": max_speakers},
        )

        logger.info(f"Zadanie transkrypcji {job_name} zostało uruchomione")
        return response
    except ClientError as e:
        logger.error(f"Błąd podczas uruchamiania zadania transkrypcji: {e}")
        return None


def get_transcription_job_status(job_name):
    """
    Sprawdza status zadania transkrypcji.

    Args:
        job_name: Nazwa zadania transkrypcji

    Returns:
        dict: Informacje o zadaniu lub None w przypadku błędu
    """
    try:
        transcribe_client = boto3.client("transcribe")
        response = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
        return response
    except ClientError as e:
        logger.error(f"Błąd podczas sprawdzania statusu zadania: {e}")
        return None


def wait_for_job_completion(job_name, poll_interval=5, max_wait_time=300):
    """
    Czeka na zakończenie zadania transkrypcji sprawdzając jego status okresowo.

    Args:
        job_name: Nazwa zadania transkrypcji
        poll_interval: Czas w sekundach między kolejnymi sprawdzeniami (domyślnie 5s)
        max_wait_time: Maksymalny czas oczekiwania w sekundach (domyślnie 5 minut)

    Returns:
        dict: Informacje o zakończonym zadaniu lub None w przypadku błędu
    """
    logger.info(f"Oczekiwanie na zakończenie zadania transkrypcji {job_name}...")

    start_time = time.time()

    while True:
        # Check if we've exceeded max wait time
        if time.time() - start_time > max_wait_time:
            logger.error(f"Timeout: Zadanie {job_name} nie zakończyło się w ciągu {max_wait_time} sekund")
            return None

        job_info = get_transcription_job_status(job_name)

        if job_info is None:
            return None

        status = job_info["TranscriptionJob"]["TranscriptionJobStatus"]

        if status == "COMPLETED":
            logger.info(f"Zadanie transkrypcji {job_name} zakończone pomyślnie")
            return job_info
        elif status == "FAILED":
            logger.error(
                f"Zadanie transkrypcji {job_name} zakończone niepowodzeniem: "
                f"{job_info['TranscriptionJob'].get('FailureReason', 'Nieznany błąd')}"
            )
            return None

        logger.info(f"Status zadania: {status}, sprawdzę ponownie za {poll_interval} sekund...")
        time.sleep(poll_interval)


def download_transcription_result(transcript_url):
    """
    Pobiera wynik transkrypcji z podanego URL.

    Args:
        transcript_url: URL do pliku z wynikami transkrypcji

    Returns:
        dict: Dane transkrypcji w formacie JSON lub None w przypadku błędu
    """
    try:
        logger.info(f"Downloading transcription result from: {transcript_url}")
        response = requests.get(transcript_url)
        response.raise_for_status()  # Zgłosi wyjątek dla błędów HTTP

        logger.info("Pobrano wyniki transkrypcji")
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Błąd podczas pobierania wyników transkrypcji: {e}")
        logger.error(f"URL: {transcript_url}")
        return None


def cleanup_resources(bucket_name, job_name=None):
    """
    Opcjonalnie czyści zasoby utworzone podczas procesu transkrypcji.

    Args:
        bucket_name: Nazwa bucketu S3 do usunięcia
        job_name: Nazwa zadania transkrypcji do usunięcia (opcjonalnie)
    """
    try:
        # Usuń bucket S3 wraz z zawartością
        if bucket_name:
            s3 = boto3.resource("s3")
            bucket = s3.Bucket(bucket_name)
            bucket.objects.all().delete()
            bucket.delete()
            logger.info(f"Bucket {bucket_name} został usunięty")

        # Możemy też usunąć zadanie transkrypcji, ale AWS samo usuwa stare zadania
        if job_name:
            transcribe_client = boto3.client("transcribe")
            transcribe_client.delete_transcription_job(TranscriptionJobName=job_name)
            logger.info(f"Zadanie transkrypcji {job_name} zostało usunięte")
    except ClientError as e:
        logger.error(f"Błąd podczas czyszczenia zasobów: {e}")


def delete_file_from_s3(bucket_name, object_name):
    """
    Usuwa plik z bucketu S3.

    Args:
        bucket_name: Nazwa bucketu S3
        object_name: Nazwa obiektu w S3 do usunięcia

    Returns:
        bool: True jeśli plik został usunięty, False w przypadku błędu
    """
    try:
        s3 = boto3.resource("s3")
        s3.Object(bucket_name, object_name).delete()
        logger.info(f"Usunięto plik {object_name} z bucketu {bucket_name}")
        return True
    except ClientError as e:
        logger.error(f"Błąd podczas usuwania pliku z S3: {e}")
        return False


def calculate_service_cost(audio_length_seconds, language_code="pl-PL"):
    """
    Oblicza szacunkowy koszt usługi transkrypcji AWS.

    Args:
        audio_length_seconds: Długość pliku audio w sekundach
        language_code: Kod języka transkrypcji

    Returns:
        dict: Słownik z informacjami o kosztach
    """
    # Aktualne ceny AWS (stan na maj 2025)
    transcribe_price_per_second = 0.0004  # USD za sekundę audio
    s3_storage_price_per_gb_month = 0.023  # USD za GB/miesiąc
    s3_price_put_request = 0.000005  # USD za żądanie PUT
    s3_price_get_request = 0.0000004  # USD za żądanie GET

    # Średni rozmiar pliku WAV - około 10MB za minutę
    estimated_file_size_mb = (audio_length_seconds / 60) * 10
    estimated_file_size_gb = estimated_file_size_mb / 1024

    # Kalkulacje
    transcribe_cost = audio_length_seconds * transcribe_price_per_second
    s3_storage_cost = estimated_file_size_gb * s3_storage_price_per_gb_month / 30  # koszt dzienny
    s3_request_cost = s3_price_put_request * 2 + s3_price_get_request * 3  # przykładowa liczba żądań

    total_cost = transcribe_cost + s3_storage_cost + s3_request_cost

    return {
        "audio_length_seconds": audio_length_seconds,
        "audio_size_mb": estimated_file_size_mb,
        "transcribe_cost": transcribe_cost,
        "s3_storage_cost": s3_storage_cost,
        "s3_request_cost": s3_request_cost,
        "total_cost": total_cost,
        "currency": "USD",
    }


def get_supported_languages():
    """
    Zwraca słownik wspieranych języków.

    Returns:
        dict: Słownik kodów języków i ich opisów
    """
    return {
        "pl-PL": "polski",
        "es-ES": "hiszpański",
        "en-US": "angielski (USA)",
        "en-GB": "angielski (UK)",
        "de-DE": "niemiecki",
        "fr-FR": "francuski",
        "it-IT": "włoski",
        "pt-PT": "portugalski",
        "ru-RU": "rosyjski",
    }
