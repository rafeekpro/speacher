#!/usr/bin/env python3
"""
Google Cloud Platform Service Module

Moduł zawierający funkcje do interakcji z usługami Google Cloud Platform:
- Google Cloud Storage do przechowywania plików audio
- Google Cloud Speech-to-Text do transkrypcji mowy na tekst
"""

import logging
import os
import time
import uuid
from datetime import datetime

from google.cloud import speech, storage
from google.protobuf.json_format import MessageToDict

# Konfiguracja loggera
logger = logging.getLogger(__name__)


def create_unique_bucket_name(base_name="audio-transcription"):
    """Tworzy unikalną nazwę dla bucketu Google Cloud Storage."""
    # Dodajemy losowy UUID do nazwy aby była unikalna
    unique_id = str(uuid.uuid4())[:8]
    return f"{base_name}-{unique_id}".lower()  # Nazwy bucketów w GCP muszą być małymi literami


def create_storage_bucket(bucket_name, project_id, location="us-central1"):
    """
    Tworzy bucket w Google Cloud Storage.

    Args:
        bucket_name: Nazwa dla nowego bucketu
        project_id: ID projektu Google Cloud
        location: Lokalizacja dla bucketu (np. us-central1)

    Returns:
        bool: True jeśli bucket został utworzony, False w przypadku błędu
    """
    try:
        # Utwórz klienta dla Google Cloud Storage
        storage_client = storage.Client(project=project_id)

        # Sprawdź czy bucket już istnieje
        if storage_client.lookup_bucket(bucket_name):
            logger.info(f"Bucket {bucket_name} już istnieje, używam istniejącego")
            return True

        # Utwórz bucket
        bucket = storage_client.create_bucket(bucket_name, location=location)

        logger.info(f"Bucket {bucket_name} został utworzony w lokalizacji {location}")
        return True
    except Exception as e:
        logger.error(f"Błąd podczas tworzenia bucketu: {e}")
        return False


def upload_file_to_storage(file_path, bucket_name, project_id, blob_name=None):
    """
    Wgrywa plik do bucketu Google Cloud Storage.

    Args:
        file_path: Ścieżka do pliku lokalnego
        bucket_name: Nazwa bucketu
        project_id: ID projektu Google Cloud
        blob_name: Nazwa obiektu w Storage (jeśli None, używa nazwy pliku)

    Returns:
        str: URI do wgranego pliku lub None w przypadku błędu
    """
    if blob_name is None:
        blob_name = os.path.basename(file_path)

    try:
        # Utwórz klienta dla Google Cloud Storage
        storage_client = storage.Client(project=project_id)

        # Pobierz bucket
        bucket = storage_client.get_bucket(bucket_name)

        # Utwórz blob
        blob = bucket.blob(blob_name)

        # Wgraj plik
        blob.upload_from_filename(file_path)

        logger.info(f"Plik {file_path} został wgrany do bucketu {bucket_name} jako {blob_name}")

        # Ustaw publiczny dostęp do obiektu na czas zadania transkrypcji
        blob.make_public()

        # Zwróć URI do pliku
        gcs_uri = f"gs://{bucket_name}/{blob_name}"
        public_url = blob.public_url

        logger.info(f"URI do pliku: {gcs_uri}")
        logger.info(f"Publiczny URL do pliku: {public_url}")

        return gcs_uri
    except Exception as e:
        logger.error(f"Błąd podczas wgrywania pliku: {e}")
        return None


def start_transcription_job(gcs_uri, project_id, job_name=None, language_code="pl-PL", max_speakers=5):
    """
    Uruchamia zadanie transkrypcji audio w Google Cloud Speech-to-Text.

    Args:
        gcs_uri: URI do pliku audio w Google Cloud Storage
        project_id: ID projektu Google Cloud
        job_name: Opcjonalna nazwa zadania
        language_code: Kod języka (default: pl-PL)
        max_speakers: Maksymalna liczba mówców do identyfikacji

    Returns:
        dict: Informacje o zadaniu transkrypcji lub None w przypadku błędu
    """
    try:
        if job_name is None:
            job_name = f"transcription-{uuid.uuid4()}"

        # Utwórz klienta dla Google Cloud Speech-to-Text
        client = speech.SpeechClient()

        # Przygotuj konfigurację rozpoznawania mowy
        audio = speech.RecognitionAudio(uri=gcs_uri)

        # Określ format audio - zakładamy WAV
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,  # Hz - to trzeba dostosować do faktycznego pliku
            language_code=language_code,
            diarization_config=speech.SpeakerDiarizationConfig(
                enable_speaker_diarization=True, min_speaker_count=1, max_speaker_count=max_speakers
            ),
            enable_automatic_punctuation=True,
            enable_word_time_offsets=True,
        )

        # Uruchom długotrwałe zadanie rozpoznawania mowy
        operation = client.long_running_recognize(config=config, audio=audio)

        # Zwróć informacje o zadaniu
        job_info = {
            "name": operation.name if hasattr(operation, "name") else job_name,
            "operation": str(operation.operation),
            "done": operation.done(),
            "project_id": project_id,
            "gcs_uri": gcs_uri,
            "language_code": language_code,
            "max_speakers": max_speakers,
            "timestamp": datetime.now().isoformat(),
        }

        logger.info(f"Zadanie transkrypcji {job_name} zostało uruchomione")
        return job_info
    except Exception as e:
        logger.error(f"Błąd podczas uruchamiania zadania transkrypcji: {e}")
        return None


def get_transcription_job_status(operation_name, project_id):
    """
    Sprawdza status zadania transkrypcji w Google Cloud Speech-to-Text.

    Args:
        operation_name: Nazwa operacji
        project_id: ID projektu Google Cloud

    Returns:
        dict: Informacje o zadaniu lub None w przypadku błędu
    """
    try:
        # Utwórz klienta dla Google Cloud Speech-to-Text
        client = speech.SpeechClient()

        # Pobierz operację
        operation = client.transport._operations_client.get_operation(operation_name)

        # Przygotuj informacje o statusie zadania
        job_info = {
            "operation": operation_name,
            "done": operation.done,
            "metadata": MessageToDict(operation.metadata) if operation.metadata else None,
            "response": MessageToDict(operation.response) if operation.response else None,
            "error": MessageToDict(operation.error) if operation.error else None,
        }

        return job_info
    except Exception as e:
        logger.error(f"Błąd podczas sprawdzania statusu zadania: {e}")
        return None


def wait_for_job_completion(operation_name, project_id, poll_interval=30):
    """
    Czeka na zakończenie zadania transkrypcji sprawdzając jego status okresowo.

    Args:
        operation_name: Nazwa operacji
        project_id: ID projektu Google Cloud
        poll_interval: Czas w sekundach między kolejnymi sprawdzeniami

    Returns:
        dict: Informacje o zakończonym zadaniu lub None w przypadku błędu
    """
    logger.info(f"Oczekiwanie na zakończenie zadania transkrypcji {operation_name}...")

    while True:
        job_info = get_transcription_job_status(operation_name, project_id)

        if job_info is None:
            return None

        if job_info["done"]:
            if job_info.get("error"):
                logger.error(f"Zadanie transkrypcji zakończone niepowodzeniem: {job_info['error']}")
                return None
            else:
                logger.info(f"Zadanie transkrypcji {operation_name} zakończone pomyślnie")
                return job_info

        logger.info(f"Zadanie w trakcie przetwarzania, sprawdzę ponownie za {poll_interval} sekund...")
        time.sleep(poll_interval)


def download_transcription_result(operation_name, project_id):
    """
    Pobiera wyniki transkrypcji dla zakończonego zadania.

    Args:
        operation_name: Nazwa operacji
        project_id: ID projektu Google Cloud

    Returns:
        dict: Dane transkrypcji lub None w przypadku błędu
    """
    try:
        # Utwórz klienta dla Google Cloud Speech-to-Text
        client = speech.SpeechClient()

        # Pobierz operację
        operation = client.transport._operations_client.get_operation(operation_name)

        if not operation.done:
            logger.error("Zadanie transkrypcji nie zostało jeszcze zakończone")
            return None

        if operation.error:
            logger.error(f"Wystąpił błąd podczas transkrypcji: {operation.error}")
            return None

        # Pobierz wyniki
        response = operation.response

        # Przygotuj dane w formacie zbliżonym do używanego w AWS/Azure
        result = {
            "results": {
                "transcripts": [],
                "items": [],
                "speaker_labels": {
                    "speakers": operation.response.speaker_count if hasattr(operation.response, "speaker_count") else 0,
                    "segments": [],
                },
            }
        }

        # Konwersja rezultatów Google do wspólnego formatu
        for alternative in response.results[-1].alternatives:
            result["results"]["transcripts"].append({"transcript": alternative.transcript})

            for word_info in alternative.words:
                item = {
                    "start_time": word_info.start_time.seconds + word_info.start_time.nanos / 1e9,
                    "end_time": word_info.end_time.seconds + word_info.end_time.nanos / 1e9,
                    "alternatives": [{"content": word_info.word}],
                    "type": "pronunciation",
                }

                # Dodaj informacje o mówiącym, jeśli są dostępne
                if hasattr(word_info, "speaker_tag"):
                    speaker_label = f"spk_{word_info.speaker_tag}"

                    # Dodaj segment mówcy
                    segment = {
                        "start_time": item["start_time"],
                        "end_time": item["end_time"],
                        "speaker_label": speaker_label,
                    }

                    result["results"]["speaker_labels"]["segments"].append(segment)

                result["results"]["items"].append(item)

        logger.info("Pobrano wyniki transkrypcji")
        return result
    except Exception as e:
        logger.error(f"Błąd podczas pobierania wyników transkrypcji: {e}")
        return None


def cleanup_resources(bucket_name, project_id, blob_name=None):
    """
    Opcjonalnie czyści zasoby utworzone podczas procesu transkrypcji.

    Args:
        bucket_name: Nazwa bucketu do usunięcia
        project_id: ID projektu Google Cloud
        blob_name: Nazwa pliku do usunięcia (jeśli None, usuwa cały bucket)
    """
    try:
        # Utwórz klienta dla Google Cloud Storage
        storage_client = storage.Client(project=project_id)

        if blob_name:
            # Usuń tylko określony plik
            bucket = storage_client.get_bucket(bucket_name)
            blob = bucket.blob(blob_name)
            blob.delete()
            logger.info(f"Usunięto plik {blob_name} z bucketu {bucket_name}")
        else:
            # Usuń bucket wraz z zawartością
            bucket = storage_client.get_bucket(bucket_name)
            blobs = bucket.list_blobs()
            for blob in blobs:
                blob.delete()
            bucket.delete()
            logger.info(f"Bucket {bucket_name} wraz z zawartością został usunięty")
    except Exception as e:
        logger.error(f"Błąd podczas czyszczenia zasobów: {e}")


def delete_file_from_storage(bucket_name, project_id, blob_name):
    """
    Usuwa plik z bucketu Google Cloud Storage.

    Args:
        bucket_name: Nazwa bucketu
        project_id: ID projektu Google Cloud
        blob_name: Nazwa obiektu w Storage do usunięcia

    Returns:
        bool: True jeśli plik został usunięty, False w przypadku błędu
    """
    try:
        # Utwórz klienta dla Google Cloud Storage
        storage_client = storage.Client(project=project_id)

        # Pobierz bucket
        bucket = storage_client.get_bucket(bucket_name)

        # Utwórz blob
        blob = bucket.blob(blob_name)

        # Usuń blob
        blob.delete()

        logger.info(f"Usunięto plik {blob_name} z bucketu {bucket_name}")
        return True
    except Exception as e:
        logger.error(f"Błąd podczas usuwania pliku z bucketu: {e}")
        return False


def calculate_service_cost(audio_length_seconds, language_code="pl-PL"):
    """
    Oblicza szacunkowy koszt usługi transkrypcji Google Cloud.

    Args:
        audio_length_seconds: Długość pliku audio w sekundach
        language_code: Kod języka transkrypcji

    Returns:
        dict: Słownik z informacjami o kosztach
    """
    # Aktualne ceny Google Cloud (stan na maj 2025)
    # Ceny dla usługi Speech-to-Text
    basic_transcribe_price_per_minute = 0.016  # USD za minutę audio (standard model)
    enhanced_transcribe_price_per_minute = 0.024  # USD za minutę audio (enhanced model)
    diarization_price_per_minute = 0.004  # Dodatkowy koszt za identyfikację mówców

    # Używamy enhanced model + diarization
    transcribe_price_per_minute = enhanced_transcribe_price_per_minute + diarization_price_per_minute

    # Ceny dla Google Cloud Storage (standard)
    storage_price_per_gb_month = 0.020  # USD za GB/miesiąc
    operation_price_per_10000 = 0.05  # USD za 10,000 operacji class A

    # Średni rozmiar pliku WAV - około 10MB za minutę
    estimated_file_size_mb = (audio_length_seconds / 60) * 10
    estimated_file_size_gb = estimated_file_size_mb / 1024

    # Kalkulacje
    audio_length_minutes = audio_length_seconds / 60
    transcribe_cost = audio_length_minutes * transcribe_price_per_minute
    storage_cost = estimated_file_size_gb * storage_price_per_gb_month / 30  # koszt dzienny
    operation_cost = (5 / 10000) * operation_price_per_10000  # ~5 operacji

    total_cost = transcribe_cost + storage_cost + operation_cost

    return {
        "audio_length_seconds": audio_length_seconds,
        "audio_length_minutes": audio_length_minutes,
        "audio_size_mb": estimated_file_size_mb,
        "transcribe_cost": transcribe_cost,
        "storage_cost": storage_cost,
        "operation_cost": operation_cost,
        "total_cost": total_cost,
        "currency": "USD",
    }


def get_supported_languages():
    """
    Zwraca słownik wspieranych języków w Google Cloud Speech-to-Text.

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
        "cs-CZ": "czeski",
        "da-DK": "duński",
        "fi-FI": "fiński",
        "ja-JP": "japoński",
        "ko-KR": "koreański",
        "nl-NL": "niderlandzki",
        "no-NO": "norweski",
        "sv-SE": "szwedzki",
        "zh-CN": "chiński (uproszczony)",
        "zh-TW": "chiński (tradycyjny)",
    }


def transcribe_short_audio(audio_file_path, project_id, language_code="pl-PL", max_speakers=1):
    """
    Wykonuje synchroniczną transkrypcję krótkiego pliku audio (do 60 sekund).
    Jest to szybsza alternatywa dla długich zadań asynchronicznych dla krótkich nagrań.

    Args:
        audio_file_path: Ścieżka do pliku audio lokalnego
        project_id: ID projektu Google Cloud
        language_code: Kod języka (default: pl-PL)
        max_speakers: Liczba mówców (domyślnie 1 dla synchronicznej transkrypcji)

    Returns:
        str: Tekst transkrypcji lub None w przypadku błędu
    """
    try:
        # Utwórz klienta dla Google Cloud Speech-to-Text
        client = speech.SpeechClient()

        # Wczytaj plik audio
        with open(audio_file_path, "rb") as audio_file:
            content = audio_file.read()

        audio = speech.RecognitionAudio(content=content)

        # Określ format audio - zakładamy WAV
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,  # Hz - to trzeba dostosować do faktycznego pliku
            language_code=language_code,
            enable_automatic_punctuation=True,
        )

        logger.info(f"Rozpoczynam synchroniczną transkrypcję pliku {audio_file_path}")

        # Wykonaj rozpoznawanie (synchroniczne)
        response = client.recognize(config=config, audio=audio)

        # Zbierz wyniki
        transcription = ""
        for result in response.results:
            transcription += result.alternatives[0].transcript + " "

        if transcription:
            logger.info("Transkrypcja pomyślna")
            return transcription.strip()
        else:
            logger.warning("Nie rozpoznano mowy w pliku audio")
            return None
    except Exception as e:
        logger.error(f"Błąd podczas transkrypcji: {e}")
        return None


def detect_audio_properties(audio_file_path):
    """
    Wykrywa właściwości pliku audio takie jak częstotliwość próbkowania.
    Wymaga biblioteki pydub.

    Args:
        audio_file_path: Ścieżka do pliku audio

    Returns:
        dict: Właściwości pliku audio lub None w przypadku błędu
    """
    try:
        # Import biblioteki tylko gdy funkcja jest używana
        from pydub import AudioSegment

        audio = AudioSegment.from_file(audio_file_path)

        properties = {
            "channels": audio.channels,
            "sample_width": audio.sample_width,
            "frame_rate": audio.frame_rate,
            "frame_width": audio.frame_width,
            "length_seconds": len(audio) / 1000.0,
            "length_ms": len(audio),
            "frame_count": int(len(audio) / 1000.0 * audio.frame_rate),
        }

        logger.info(f"Wykryto właściwości audio dla pliku {audio_file_path}: {properties}")
        return properties
    except ImportError:
        logger.warning("Nie można wykryć właściwości audio - biblioteka pydub nie jest zainstalowana")
        # Return default properties
        return {
            "channels": 1,
            "sample_width": 2,
            "frame_rate": 16000,
            "frame_width": 2,
            "length_seconds": 0,
            "length_ms": 0,
            "frame_count": 0,
        }
    except Exception as e:
        logger.error(f"Błąd podczas wykrywania właściwości audio: {e}")
        return None
