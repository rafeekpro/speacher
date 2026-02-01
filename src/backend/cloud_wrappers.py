"""
Cloud service wrappers for backend API
"""

import logging
import os
import boto3
import time
from typing import Any, Dict, Optional
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class AWSService:
    """AWS service wrapper for transcription"""

    def __init__(self):
        self.s3_client = boto3.client("s3")
        self.transcribe_client = boto3.client("transcribe")

    def upload_file_to_s3(self, file_path: str, bucket_name: str, object_name: str) -> str:
        """Upload file to S3"""
        try:
            self.s3_client.upload_file(file_path, bucket_name, object_name)
            return f"s3://{bucket_name}/{object_name}"
        except ClientError as e:
            raise Exception(f"Failed to upload to S3: {e}")

    def start_transcription_job(
        self, job_name: str, media_file_uri: str, media_format: str, language_code: str, settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Start AWS Transcribe job"""
        try:
            response = self.transcribe_client.start_transcription_job(
                TranscriptionJobName=job_name,
                Media={"MediaFileUri": media_file_uri},
                MediaFormat=media_format,
                LanguageCode=language_code,
                Settings=settings,
            )
            return response
        except ClientError as e:
            raise Exception(f"Failed to start transcription job: {e}")

    def wait_for_job_completion(self, job_name: str, timeout: int = 3600) -> Dict[str, Any]:
        """Wait for transcription job to complete"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = self.transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
                status = response["TranscriptionJob"]["TranscriptionJobStatus"]

                if status == "COMPLETED":
                    return response["TranscriptionJob"]
                elif status == "FAILED":
                    raise Exception(
                        f"Transcription job failed: {response['TranscriptionJob'].get('FailureReason', 'Unknown')}"
                    )

                time.sleep(10)
            except ClientError as e:
                time.sleep(10)

        raise Exception("Transcription job timed out")

    def get_transcription_job_status(self, job_name: str) -> Dict[str, Any]:
        """Get transcription job status"""
        try:
            response = self.transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
            return response["TranscriptionJob"]
        except ClientError as e:
            raise Exception(f"Failed to get job status: {e}")

    def download_transcription_result(self, transcript_uri: str) -> Dict[str, Any]:
        """Download transcription result from S3"""
        try:
            # Parse S3 URI
            parts = transcript_uri.replace("s3://", "").split("/")
            bucket_name = parts[0]
            object_name = "/".join(parts[1:])

            response = self.s3_client.get_object(Bucket=bucket_name, Key=object_name)
            import json

            return json.loads(response["Body"].read().decode("utf-8"))
        except ClientError as e:
            raise Exception(f"Failed to download transcription: {e}")

    def delete_file_from_s3(self, bucket_name: str, object_name: str) -> bool:
        """Delete file from S3"""
        try:
            self.s3_client.delete_object(Bucket=bucket_name, Key=object_name)
            return True
        except ClientError as e:
            raise Exception(f"Failed to delete from S3: {e}")


# Create AWS service instance
aws_service = AWSService()


# Azure wrappers
def upload_to_blob(
    file_path: str, storage_account: str, storage_key: str, container_name: str, blob_name: str
) -> Optional[str]:
    """Upload file to Azure Blob Storage"""
    try:
        from azure.storage.blob import BlobServiceClient

        connection_string = f"DefaultEndpointsProtocol=https;AccountName={storage_account};AccountKey={storage_key};EndpointSuffix=core.windows.net"
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)

        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)

        with open(file_path, "rb") as data:
            blob_client.upload_blob(data, overwrite=True)

        return blob_client.url
    except Exception as e:
        logger.error(f"Failed to upload to Azure Blob: {e}")
        return None


def transcribe_from_blob(
    blob_url: str, language: str, enable_diarization: bool, max_speakers: Optional[int]
) -> Optional[Dict[str, Any]]:
    """Transcribe audio from Azure Blob using Azure Speech Services"""
    try:
        # This would normally use Azure Speech SDK
        # For now, return mock response
        return {
            "displayText": "Azure transcription placeholder",
            "duration": 10000000,  # 1 second in 100-nanosecond units
        }
    except Exception as e:
        logger.error(f"Failed to transcribe from Azure: {e}")
        return None


def delete_blob(storage_account: str, storage_key: str, container_name: str, blob_name: str) -> bool:
    """Delete blob from Azure Storage"""
    try:
        from azure.storage.blob import BlobServiceClient

        connection_string = f"DefaultEndpointsProtocol=https;AccountName={storage_account};AccountKey={storage_key};EndpointSuffix=core.windows.net"
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)

        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)

        blob_client.delete_blob()
        return True
    except Exception as e:
        logger.error(f"Failed to delete Azure blob: {e}")
        return False


# GCP wrappers
def upload_to_gcs(file_path: str, bucket_name: str, blob_name: str) -> Optional[str]:
    """Upload file to Google Cloud Storage"""
    try:
        from google.cloud import storage

        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        blob.upload_from_filename(file_path)

        return f"gs://{bucket_name}/{blob_name}"
    except Exception as e:
        logger.error(f"Failed to upload to GCS: {e}")
        return None


def transcribe_from_gcs(
    gcs_uri: str, language: str, enable_diarization: bool, max_speakers: Optional[int]
) -> Optional[Dict[str, Any]]:
    """Transcribe audio from GCS using Google Speech-to-Text"""
    try:
        from google.cloud import speech

        client = speech.SpeechClient()

        audio = speech.RecognitionAudio(uri=gcs_uri)

        diarization_config = None
        if enable_diarization:
            diarization_config = speech.SpeakerDiarizationConfig(
                enable_speaker_diarization=True, max_speaker_count=max_speakers or 4
            )

        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            language_code=language,
            diarization_config=diarization_config,
        )

        operation = client.long_running_recognize(config=config, audio=audio)
        response = operation.result()

        results = []
        for result in response.results:
            results.append({"alternatives": [{"transcript": result.alternatives[0].transcript}]})

        return {"results": results}
    except Exception as e:
        logger.error(f"Failed to transcribe from GCS: {e}")
        return None


def delete_from_gcs(bucket_name: str, blob_name: str) -> bool:
    """Delete object from Google Cloud Storage"""
    try:
        from google.cloud import storage

        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        blob.delete()
        return True
    except Exception as e:
        logger.error(f"Failed to delete from GCS: {e}")
        return False
