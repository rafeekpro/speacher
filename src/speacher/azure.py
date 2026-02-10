#!/usr/bin/env python3
"""
Azure Service Module

Moduł zawierający funkcje do interakcji z usługami Azure:
- Azure Blob Storage do przechowywania plików audio
- Azure Speech Service do transkrypcji mowy na tekst
"""

import logging
import os
import time
import uuid
from datetime import datetime, timedelta

import requests
from azure.cognitiveservices.speech import CancellationDetails, ResultReason, SpeechConfig, SpeechRecognizer
from azure.cognitiveservices.speech.audio import AudioConfig
from azure.core.exceptions import ResourceExistsError
from azure.storage.blob import (
    BlobServiceClient,
    ContainerSasPermissions,
    generate_container_sas,
)

# Konfiguracja loggera
logger = logging.getLogger(__name__)


def create_unique_container_name(base_name="audio-transcription"):
    """Tworzy unikalną nazwę dla kontenera Blob Storage."""
    # Dodajemy losowy UUID do nazwy aby była unikalna
    unique_id = str(uuid.uuid4())[:8]
    return f"{base_name}{unique_id}".lower()  # Nazwy kontenerów w Azure muszą być małymi literami


def create_blob_container(storage_account_connection_string, container_name):
    """
    Tworzy kontener w Azure Blob Storage.

    Args:
        storage_account_connection_string: Connection string do konta Storage
        container_name: Nazwa dla nowego kontenera

    Returns:
        bool: True jeśli kontener został utworzony, False w przypadku błędu
    """
    try:
        # Utwórz klienta dla Blob Storage
        blob_service_client = BlobServiceClient.from_connection_string(storage_account_connection_string)

        # Utwórz kontener
        container_client = blob_service_client.create_container(container_name)

        logger.info(f"Kontener {container_name} został utworzony")
        return True
    except ResourceExistsError:
        logger.info(f"Kontener {container_name} już istnieje, używam istniejącego")
        return True
    except Exception as e:
        logger.error(f"Błąd podczas tworzenia kontenera: {e}")
        return False


def upload_file_to_blob(file_path, storage_account_connection_string, container_name, blob_name=None):
    """
    Wgrywa plik do kontenera Azure Blob Storage.

    Args:
        file_path: Ścieżka do pliku lokalnego
        storage_account_connection_string: Connection string do konta Storage
        container_name: Nazwa kontenera
        blob_name: Nazwa obiektu w Storage (jeśli None, używa nazwy pliku)

    Returns:
        str: URL do wgranego pliku lub None w przypadku błędu
    """
    if blob_name is None:
        blob_name = os.path.basename(file_path)

    try:
        # Utwórz klienta dla Blob Storage
        blob_service_client = BlobServiceClient.from_connection_string(storage_account_connection_string)

        # Utwórz klienta dla danego kontenera
        container_client = blob_service_client.get_container_client(container_name)

        # Utwórz klienta dla danego blob
        blob_client = container_client.get_blob_client(blob_name)

        # Wgraj plik
        with open(file_path, "rb") as data:
            blob_client.upload_blob(data, overwrite=True)

        logger.info(f"Plik {file_path} został wgrany do kontenera {container_name} jako {blob_name}")

        # Wygeneruj SAS token dla dostępu do pliku
        sas_token = generate_container_sas(
            account_name=blob_service_client.account_name,
            container_name=container_name,
            account_key=blob_service_client.credential.account_key,
            permission=ContainerSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(hours=1),
        )

        # Zwróć URL do pliku
        blob_url = (
            f"https://{blob_service_client.account_name}.blob.core.windows.net/{container_name}/{blob_name}?{sas_token}"
        )
        return blob_url
    except Exception as e:
        logger.error(f"Błąd podczas wgrywania pliku: {e}")
        return None


def start_transcription_job(subscription_key, region, audio_url, job_name=None, language_code="pl-PL", max_speakers=5):
    """
    Uruchamia zadanie transkrypcji audio w Azure Speech Service.

    Args:
        subscription_key: Klucz subskrypcji Azure Speech Service
        region: Region Azure (np. westeurope)
        audio_url: URL do pliku audio
        job_name: Opcjonalna nazwa zadania
        language_code: Kod języka (default: pl-PL)
        max_speakers: Maksymalna liczba mówców do identyfikacji

    Returns:
        dict: Informacje o zadaniu transkrypcji lub None w przypadku błędu
    """
    try:
        if job_name is None:
            job_name = f"transcription-{uuid.uuid4()}"

        # Przygotuj URL endpoint dla Azure Speech Service Batch Transcription
        endpoint = f"https://{region}.api.cognitive.microsoft.com/speechtotext/v3.1/transcriptions"

        # Przygotuj nagłówki żądania
        headers = {"Ocp-Apim-Subscription-Key": subscription_key, "Content-Type": "application/json"}

        # Przygotuj dane żądania
        data = {
            "contentUrls": [audio_url],
            "locale": language_code,
            "displayName": job_name,
            "properties": {
                "diarizationEnabled": True,
                "wordLevelTimestampsEnabled": True,
                "punctuationMode": "Automatic",
                "profanityFilterMode": "None",
                "diarization": {"speakers": {"maxCount": max_speakers}},
            },
        }

        # Wyślij żądanie utworzenia transkrypcji
        response = requests.post(endpoint, headers=headers, json=data)
        response.raise_for_status()

        job_info = response.json()
        logger.info(f"Zadanie transkrypcji {job_name} zostało uruchomione")
        return job_info
    except Exception as e:
        logger.error(f"Błąd podczas uruchamiania zadania transkrypcji: {e}")
        return None


def get_transcription_job_status(subscription_key, region, job_id):
    """
    Sprawdza status zadania transkrypcji w Azure Speech Service.

    Args:
        subscription_key: Klucz subskrypcji Azure Speech Service
        region: Region Azure (np. westeurope)
        job_id: Identyfikator zadania transkrypcji

    Returns:
        dict: Informacje o zadaniu lub None w przypadku błędu
    """
    try:
        # Przygotuj URL endpoint dla sprawdzenia statusu zadania
        endpoint = f"https://{region}.api.cognitive.microsoft.com/speechtotext/v3.1/transcriptions/{job_id}"

        # Przygotuj nagłówki żądania
        headers = {"Ocp-Apim-Subscription-Key": subscription_key}

        # Wyślij żądanie sprawdzenia statusu
        response = requests.get(endpoint, headers=headers)
        response.raise_for_status()

        return response.json()
    except Exception as e:
        logger.error(f"Błąd podczas sprawdzania statusu zadania: {e}")
        return None


def wait_for_job_completion(subscription_key, region, job_id, poll_interval=30):
    """
    Czeka na zakończenie zadania transkrypcji sprawdzając jego status okresowo.

    Args:
        subscription_key: Klucz subskrypcji Azure Speech Service
        region: Region Azure (np. westeurope)
        job_id: Identyfikator zadania transkrypcji
        poll_interval: Czas w sekundach między kolejnymi sprawdzeniami

    Returns:
        dict: Informacje o zakończonym zadaniu lub None w przypadku błędu
    """
    logger.info(f"Oczekiwanie na zakończenie zadania transkrypcji {job_id}...")

    while True:
        job_info = get_transcription_job_status(subscription_key, region, job_id)

        if job_info is None:
            return None

        status = job_info.get("status")

        if status == "Succeeded":
            logger.info(f"Zadanie transkrypcji {job_id} zakończone pomyślnie")
            return job_info
        elif status in ["Failed", "Cancelled"]:
            logger.error(f"Zadanie transkrypcji {job_id} zakończone niepowodzeniem")
            return None

        logger.info(f"Status zadania: {status}, sprawdzę ponownie za {poll_interval} sekund...")
        time.sleep(poll_interval)


def download_transcription_result(subscription_key, result_url):
    """
    Pobiera wynik transkrypcji z podanego URL.

    Args:
        subscription_key: Klucz subskrypcji Azure Speech Service
        result_url: URL do pliku z wynikami transkrypcji

    Returns:
        dict: Dane transkrypcji w formacie JSON lub None w przypadku błędu
    """
    try:
        headers = {"Ocp-Apim-Subscription-Key": subscription_key}

        response = requests.get(result_url, headers=headers)
        response.raise_for_status()

        logger.info("Pobrano wyniki transkrypcji")
        return response.json()
    except Exception as e:
        logger.error(f"Błąd podczas pobierania wyników transkrypcji: {e}")
        return None


def cleanup_resources(
    storage_account_connection_string, container_name, subscription_key=None, region=None, job_id=None
):
    """
    Opcjonalnie czyści zasoby utworzone podczas procesu transkrypcji.

    Args:
        storage_account_connection_string: Connection string do konta Storage
        container_name: Nazwa kontenera do usunięcia
        subscription_key: Klucz subskrypcji Azure Speech Service
        region: Region Azure
        job_id: Identyfikator zadania transkrypcji do usunięcia (opcjonalnie)
    """
    try:
        # Usuń kontener Blob Storage wraz z zawartością
        if container_name:
            blob_service_client = BlobServiceClient.from_connection_string(storage_account_connection_string)
            container_client = blob_service_client.get_container_client(container_name)
            container_client.delete_container()
            logger.info(f"Kontener {container_name} został usunięty")

        # Opcjonalnie usuń zadanie transkrypcji
        if subscription_key and region and job_id:
            endpoint = f"https://{region}.api.cognitive.microsoft.com/speechtotext/v3.1/transcriptions/{job_id}"
            headers = {"Ocp-Apim-Subscription-Key": subscription_key}
            response = requests.delete(endpoint, headers=headers)
            if response.status_code == 204:
                logger.info(f"Zadanie transkrypcji {job_id} zostało usunięte")
            else:
                logger.warning(f"Nie udało się usunąć zadania transkrypcji, kod odpowiedzi: {response.status_code}")
    except Exception as e:
        logger.error(f"Błąd podczas czyszczenia zasobów: {e}")


def delete_blob_from_container(storage_account_connection_string, container_name, blob_name):
    """
    Usuwa plik z kontenera Azure Blob Storage.

    Args:
        storage_account_connection_string: Connection string do konta Storage
        container_name: Nazwa kontenera
        blob_name: Nazwa obiektu w Storage do usunięcia

    Returns:
        bool: True jeśli plik został usunięty, False w przypadku błędu
    """
    try:
        blob_service_client = BlobServiceClient.from_connection_string(storage_account_connection_string)
        container_client = blob_service_client.get_container_client(container_name)
        blob_client = container_client.get_blob_client(blob_name)
        blob_client.delete_blob()

        logger.info(f"Usunięto plik {blob_name} z kontenera {container_name}")
        return True
    except Exception as e:
        logger.error(f"Błąd podczas usuwania pliku z kontenera: {e}")
        return False


def calculate_service_cost(audio_length_seconds, language_code="pl-PL"):
    """
    Oblicza szacunkowy koszt usługi transkrypcji Azure.

    Args:
        audio_length_seconds: Długość pliku audio w sekundach
        language_code: Kod języka transkrypcji

    Returns:
        dict: Słownik z informacjami o kosztach
    """
    # Aktualne ceny Azure (stan na maj 2025)
    # Ceny dla usługi Azure Speech Service (Standard tier)
    transcribe_price_per_hour = 1.0  # USD za godzinę audio
    transcribe_price_per_second = transcribe_price_per_hour / 3600

    # Ceny dla Azure Blob Storage (Hot tier)
    storage_price_per_gb_month = 0.0184  # USD za GB/miesiąc
    transaction_price_per_10000 = 0.05  # USD za 10,000 operacji

    # Średni rozmiar pliku WAV - około 10MB za minutę
    estimated_file_size_mb = (audio_length_seconds / 60) * 10
    estimated_file_size_gb = estimated_file_size_mb / 1024

    # Kalkulacje
    transcribe_cost = audio_length_seconds * transcribe_price_per_second
    storage_cost = estimated_file_size_gb * storage_price_per_gb_month / 30  # koszt dzienny
    transaction_cost = (5 / 10000) * transaction_price_per_10000  # ~5 transakcji

    total_cost = transcribe_cost + storage_cost + transaction_cost

    return {
        "audio_length_seconds": audio_length_seconds,
        "audio_size_mb": estimated_file_size_mb,
        "transcribe_cost": transcribe_cost,
        "storage_cost": storage_cost,
        "transaction_cost": transaction_cost,
        "total_cost": total_cost,
        "currency": "USD",
    }


def get_supported_languages():
    """
    Zwraca słownik wspieranych języków w Azure Speech Service.

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
        "zh-HK": "chiński (tradycyjny, Hongkong)",
    }


def transcribe_short_audio(subscription_key, region, audio_file_path, language_code="pl-PL"):
    """
    Wykonuje transkrypcję krótkiego pliku audio (do 60 sekund) bezpośrednio za pomocą Azure Speech SDK.
    Jest to szybsza alternatywa dla długich zadań batch transcription dla krótkich nagrań.

    Args:
        subscription_key: Klucz subskrypcji Azure Speech Service
        region: Region Azure (np. westeurope)
        audio_file_path: Ścieżka do pliku audio lokalnego
        language_code: Kod języka (default: pl-PL)

    Returns:
        str: Tekst transkrypcji lub None w przypadku błędu
    """
    try:
        # Skonfiguruj usługę Speech
        speech_config = SpeechConfig(subscription=subscription_key, region=region)
        speech_config.speech_recognition_language = language_code

        # Skonfiguruj plik audio
        audio_config = AudioConfig(filename=audio_file_path)

        # Utwórz rozpoznawacz
        recognizer = SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

        logger.info(f"Rozpoczynam synchroniczną transkrypcję pliku {audio_file_path}")

        # Wykonaj rozpoznawanie
        result = recognizer.recognize_once_async().get()

        # Sprawdź wynik
        if result.reason == ResultReason.RecognizedSpeech:
            logger.info("Transkrypcja pomyślna")
            return result.text
        elif result.reason == ResultReason.NoMatch:
            logger.warning("Nie rozpoznano mowy w pliku audio")
            return None
        elif result.reason == ResultReason.Canceled:
            cancellation_details = CancellationDetails.from_result(result)
            logger.error(f"Transkrypcja anulowana: {cancellation_details.reason}")
            logger.error(f"Szczegóły błędu: {cancellation_details.error_details}")
            return None
    except Exception as e:
        logger.error(f"Błąd podczas transkrypcji: {e}")
        return None
