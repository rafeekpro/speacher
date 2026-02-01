"""
Cloud service wrappers for backend API
"""

import logging
import os
import boto3
import time
from typing import Any, Dict, List, Optional
from botocore.exceptions import ClientError

# Configure logger to output to stdout
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Add handler if not already present
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class AWSService:
    """AWS service wrapper for transcription"""

    def __init__(self, access_key_id: str = None, secret_access_key: str = None, region: str = None):
        """Initialize AWS service with credentials.

        Args:
            access_key_id: AWS access key ID (optional, reads from env if None)
            secret_access_key: AWS secret access key (optional, reads from env if None)
            region: AWS region (optional, reads from env if None)
        """
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.region = region or os.getenv("AWS_DEFAULT_REGION", "us-east-1")

        # Log credentials (safely) - using print for guaranteed output
        print(f"[AWS SERVICE] Initializing AWS service")
        if access_key_id:
            print(f"[AWS SERVICE] Access key: {access_key_id[:8]}...{access_key_id[-4:]}")
            print(f"[AWS SERVICE] Secret key length: {len(secret_access_key) if secret_access_key else 0} chars")
        else:
            print(f"[AWS SERVICE] WARNING: No access_key_id provided!")

        # Initialize clients with credentials or from environment
        client_config = {}
        if access_key_id and secret_access_key:
            client_config['aws_access_key_id'] = access_key_id
            client_config['aws_secret_access_key'] = secret_access_key

        if region:
            client_config['region_name'] = region
        elif os.getenv("AWS_DEFAULT_REGION"):
            client_config['region_name'] = os.getenv("AWS_DEFAULT_REGION")

        self.s3_client = boto3.client("s3", **client_config)
        self.transcribe_client = boto3.client("transcribe", **client_config)

    def upload_file_to_s3(self, file_path: str, bucket_name: str, object_name: str) -> str:
        """Upload file to S3"""
        try:
            logger.info(f"Uploading {file_path} to s3://{bucket_name}/{object_name}")
            self.s3_client.upload_file(file_path, bucket_name, object_name)
            logger.info(f"Upload successful: s3://{bucket_name}/{object_name}")
            return f"s3://{bucket_name}/{object_name}"
        except ClientError as e:
            logger.error(f"S3 upload error: {e}")
            raise Exception(f"Failed to upload to S3: {e}")

    def start_transcription_job(
        self, job_name: str, media_file_uri: str, media_format: str, language_code: str, settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Start AWS Transcribe job"""
        try:
            logger.info(f"Starting AWS Transcribe job: {job_name}")
            logger.info(f"  Media URI: {media_file_uri}")
            logger.info(f"  Format: {media_format}, Language: {language_code}")
            logger.info(f"  Settings: {settings}")

            response = self.transcribe_client.start_transcription_job(
                TranscriptionJobName=job_name,
                Media={"MediaFileUri": media_file_uri},
                MediaFormat=media_format,
                LanguageCode=language_code,
                Settings=settings,
            )

            logger.info(f"Job started successfully: {response['TranscriptionJob']['TranscriptionJobStatus']}")
            return response
        except ClientError as e:
            logger.error(f"Failed to start transcription job: {e}")
            raise Exception(f"Failed to start transcription job: {e}")

    def wait_for_job_completion(self, job_name: str, timeout: int = 3600) -> Dict[str, Any]:
        """Wait for transcription job to complete"""
        start_time = time.time()
        logger.info(f"Waiting for job {job_name} to complete (timeout: {timeout}s)")

        while time.time() - start_time < timeout:
            try:
                response = self.transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
                job = response.get("TranscriptionJob", {})
                status = job.get("TranscriptionJobStatus")

                logger.debug(f"Job {job_name} status: {status}")

                if status == "COMPLETED":
                    logger.info(f"Job {job_name} completed successfully")
                    return response["TranscriptionJob"]
                elif status == "FAILED":
                    failure_reason = job.get("FailureReason", "Unknown")
                    logger.error(f"Job {job_name} failed: {failure_reason}")
                    raise Exception(f"Transcription job failed: {failure_reason}")

                time.sleep(10)
            except ClientError as e:
                logger.error(f"Error checking job status for {job_name}: {e}")
                time.sleep(10)

        logger.error(f"Job {job_name} timed out after {timeout}s")
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
            import requests
            import json

            logger.info(f"Downloading transcription from: {transcript_uri}")

            # AWS Transcribe returns HTTPS URL, download it directly
            response = requests.get(transcript_uri)
            response.raise_for_status()

            data = response.json()
            logger.info(f"Successfully downloaded transcription ({len(data)} keys)")

            return data
        except Exception as e:
            logger.error(f"Failed to download transcription: {e}")
            raise Exception(f"Failed to download transcription: {e}")

    def delete_file_from_s3(self, bucket_name: str, object_name: str) -> bool:
        """Delete file from S3"""
        try:
            self.s3_client.delete_object(Bucket=bucket_name, Key=object_name)
            return True
        except ClientError as e:
            raise Exception(f"Failed to delete from S3: {e}")

    def list_s3_files(self, bucket_name: str) -> List[Dict[str, Any]]:
        """List all files in S3 bucket.

        Args:
            bucket_name: S3 bucket name

        Returns:
            List of files with metadata: key, size, last_modified, etag
        """
        try:
            logger.info(f"Listing files in S3 bucket: {bucket_name}")
            files = []

            # Use pagination to handle buckets with many objects
            paginator = self.s3_client.get_paginator('list_objects_v2')
            page_iterator = paginator.paginate(Bucket=bucket_name)

            for page in page_iterator:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        files.append({
                            'key': obj['Key'],
                            'size': obj['Size'],
                            'last_modified': obj['LastModified'],
                            'etag': obj['ETag'].strip('"')
                        })

            logger.info(f"Found {len(files)} files in bucket {bucket_name}")
            return files

        except ClientError as e:
            logger.error(f"Failed to list S3 files: {e}")
            raise Exception(f"Failed to list S3 files: {e}")


# AWS service instance will be created with credentials at runtime
aws_service = None

def get_aws_service(access_key_id: str = None, secret_access_key: str = None, region: str = None) -> AWSService:
    """Get or create AWS service instance with credentials.

    Args:
        access_key_id: AWS access key ID
        secret_access_key: AWS secret access key
        region: AWS region

    Returns:
        AWSService instance
    """
    global aws_service
    if aws_service is None or access_key_id:
        aws_service = AWSService(access_key_id, secret_access_key, region)
    return aws_service


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
