# Speacher

Speacher is a tool for transcribing WAV audio files using cloud speech-to-text services (AWS, Azure, GCP). It offers:
- A command-line interface (CLI) (AWS Transcribe by default)
- A FastAPI backend service to upload WAV files, transcribe via AWS Transcribe, and store results in MongoDB

## Project Structure
```
/
├── speacher/         # Core modules for AWS, Azure, GCP, and transcription processing
├── backend/          # FastAPI application (upload + transcription + MongoDB)
└── tests/            # Unit tests for backend API
```

## Requirements
- Python 3.7+
- AWS credentials configured (for CLI and backend):
  - AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION
- MongoDB instance (for backend API)
- Install required Python packages:
  ```bash
  pip install fastapi uvicorn pymongo boto3
  # (optional for Azure)
  pip install azure-storage-blob azure-cognitiveservices-speech requests
  # (optional for GCP)
  pip install google-cloud-storage google-cloud-speech google-auth
  ```

## CLI Usage (AWS Transcribe)
The CLI entrypoint is in `speecher/cli.py`. You can run:
```bash
python -m speacher.cli [OPTIONS]
```

Run `--help` for all options:
```bash
python -m speacher.cli --help
```
Key options:
- `--audio-file` PATH         Path to input `.wav` file (default: `audio.wav`)
- `--bucket-name` NAME        Existing S3 bucket to use (otherwise a new bucket is created)
- `--region` REGION           AWS region (default: from AWS config)
- `--language` CODE           Language code (default: `pl-PL`)
- `--max-speakers` N          Max number of speaker labels (default: 5)
- `--output-file` PATH        File to write transcript to
- `--include-timestamps`      Include timestamps in output (default: true)
- `--no-timestamps`           Disable timestamps
- `--show-cost`               Display estimated service cost

Example:
```bash
python -m speacher.cli \
  --audio-file meeting.wav \
  --bucket-name my-transcribe-bucket \
  --language en-US \
  --max-speakers 2 \
  --output-file meeting_transcript.txt
```

## Backend API (FastAPI)
The backend service accepts WAV uploads, performs AWS Transcribe, and stores transcripts in MongoDB.

### Configuration
Set environment variables:
```bash
export S3_BUCKET_NAME=<your-s3-bucket>
export MONGODB_URI="mongodb://localhost:27017"
export MONGODB_DB="speacher"
export MONGODB_COLLECTION="transcriptions"
```

Ensure AWS credentials are available in the environment or via AWS CLI config.

### Run the server
```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### Endpoint
- **POST** `/transcribe`
  - Form field: `file` (WAV audio, `Content-Type: audio/wav`)
  - Response: JSON with MongoDB document ID and transcript

Example request:
```bash
curl -X POST "http://localhost:8000/transcribe" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/audio.wav;type=audio/wav"
```

Example response:
```json
{
  "id": "605c3f9d9e1b1b3f0c1d2e4a",
  "transcript": "Hello world, this is a test transcription."
}
```

## Testing
Install pytest and run tests:
```bash
pip install pytest
pytest
```

---
_Speecher_ simplifies audio transcription workflows for CLI users and web services alike. Enjoy!  
Feel free to file issues or contribute via pull requests.