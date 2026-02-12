# 🎙️ Speacher - Multi-Cloud Speech Transcription Platform

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18+-61DAFB.svg)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178C6.svg)](https://www.typescriptlang.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Speacher** is a cloud-agnostic speech transcription platform that converts audio files to text with high accuracy. Upload your audio files through the modern React interface or API, choose your preferred cloud provider (AWS, Azure, or Google Cloud), and get accurate transcriptions with speaker identification, timestamps, and multiple export formats.

Perfect for transcribing meetings, interviews, podcasts, lectures, and any audio content in 11+ languages.

## ✨ Key Features

- 🌐 **Multi-cloud Support** - AWS Transcribe, Azure Speech Services, Google Speech-to-Text
- 🗣️ **Speaker Diarization** - Automatic recognition of up to 10 different speakers
- 🌍 **11+ Languages** - English, Spanish, French, German, Polish, and more
- ⚡ **Modern React UI** - TypeScript, responsive design with sidebar navigation
- 🚀 **FastAPI Backend** - High-performance async Python API
- 📊 **Multiple Export Formats** - TXT, SRT, JSON, VTT, PDF
- 🐳 **Docker Ready** - Complete containerization with development and production configs
- 📝 **Transcription History** - MongoDB/PostgreSQL for persistent storage

## 🚀 Quick Start (2 Minutes to Running!)

### Prerequisites
- Docker and Docker Compose installed
- At least one cloud provider account (AWS/Azure/GCP)
- 4GB RAM minimum, 8GB recommended

### Step 1: Clone and Configure

```bash
# Clone the repository
git clone https://github.com/yourusername/speacher.git
cd speacher

# Copy environment template
cp config/.env.example .env

# Edit .env and add at least one cloud provider's credentials
nano .env  # or use your favorite editor
```

**Minimum .env configuration** (you need at least one provider):

```env
# For AWS (minimum required fields)
AWS_ACCESS_KEY_ID=your_key_here
AWS_SECRET_ACCESS_KEY=your_secret_here
AWS_DEFAULT_REGION=us-east-1
S3_BUCKET_NAME=any-bucket-name

# For Azure (minimum required fields)
AZURE_STORAGE_ACCOUNT=your_account
AZURE_STORAGE_KEY=your_key
AZURE_SPEECH_KEY=your_speech_key
AZURE_SPEECH_REGION=eastus

# For Google Cloud (minimum required fields)
GCP_PROJECT_ID=your_project
GCP_BUCKET_NAME=your-bucket
GCP_CREDENTIALS_FILE=./path-to-credentials.json
```

### Step 2: Start Development Environment

```bash
# For development with hot-reload (RECOMMENDED for developers)
docker compose -f docker-compose.dev.yml up

# OR for basic setup
docker compose up
```

### Step 3: Access the Application

Open your browser and navigate to:
- 🌐 **React Frontend**: <http://localhost:3000> - Modern UI with sidebar navigation
- 📊 **API Documentation**: <http://localhost:8000/docs> - Interactive API docs (Swagger)
- 🔧 **API Endpoint**: <http://localhost:8000> - Direct API access
- 💾 **MongoDB**: `localhost:27017` - Database (if using MongoDB)
- 🐘 **PostgreSQL**: `localhost:5432` - Database (if using dev environment)

That's it! You should see the Speecher interface ready for audio transcription.

## 🎵 Supported Audio Formats

The platform supports the following audio formats:
- **WAV** - Uncompressed, best quality
- **MP3** - Most common format
- **M4A** - Apple audio format
- **MP4** - Video files (audio track extracted)
- **FLAC** - Lossless compression
- **OGG** - Open source format
- **WEBM** - Web media format

**File size limit**: 500MB (can be configured)

## 🌍 Supported Languages

| Language | Code | AWS | Azure | GCP |
|----------|------|-----|-------|-----|
| English (US) | en-US | ✅ | ✅ | ✅ |
| English (UK) | en-GB | ✅ | ✅ | ✅ |
| Spanish | es-ES | ✅ | ✅ | ✅ |
| French | fr-FR | ✅ | ✅ | ✅ |
| German | de-DE | ✅ | ✅ | ✅ |
| Italian | it-IT | ✅ | ✅ | ✅ |
| Portuguese | pt-PT | ✅ | ✅ | ✅ |
| Polish | pl-PL | ✅ | ✅ | ✅ |
| Dutch | nl-NL | ✅ | ✅ | ✅ |
| Russian | ru-RU | ✅ | ✅ | ✅ |
| Japanese | ja-JP | ✅ | ✅ | ✅ |
| Chinese (Mandarin) | zh-CN | ✅ | ✅ | ✅ |
| Korean | ko-KR | ✅ | ✅ | ✅ |

## 🐳 Docker Compose Configurations Explained

### Development Mode (`docker-compose.dev.yml`) - RECOMMENDED

Best for active development with these features:
- ✅ **Hot-reload** for both frontend and backend
- ✅ **PostgreSQL + MongoDB + Redis** for full feature set
- ✅ **Volume mounting** for instant code changes
- ✅ **Debug mode** enabled
- ✅ **Detailed logging**

```bash
docker compose -f docker-compose.dev.yml up
```

### Basic Mode (`docker-compose.yml`)

Simple setup with core features:
- ✅ MongoDB only
- ✅ Basic backend and frontend
- ✅ Good for quick testing

```bash
docker compose up
```

### Production Mode (`docker-compose.prod.yml`)

Optimized for deployment:
- ✅ PostgreSQL + Redis
- ✅ Resource limits
- ✅ Health checks
- ✅ Security hardening
- ✅ SSL/TLS support

```bash
docker compose -f docker-compose.prod.yml up
```

## 📁 Project Structure

```text
speecher/
├── src/
│   ├── backend/           # FastAPI REST API
│   ├── speecher/          # Core transcription library
│   └── react-frontend/    # React TypeScript UI
├── docker/                # Docker configurations
├── tests/                 # Test suites
├── config/                # Configuration files
└── docker-compose*.yml    # Docker compose files

## 💻 Local Installation (CLI)

### Requirements

- Python 3.11+
- Poetry or pip
- Account with AWS/Azure/GCP (at least one)

### Installation

```bash
# With Poetry
poetry install

# Or with pip
pip install -r requirements.txt
```

### CLI Usage

```bash
# Basic transcription
python -m speecher.cli --audio-file audio.wav --language pl-PL

# With file output
python -m speecher.cli --audio-file audio.wav --output-file transcript.txt

# With cost estimation
python -m speecher.cli --audio-file audio.wav --show-cost

# With speaker diarization (max 4 speakers)
python -m speecher.cli --audio-file audio.wav --enable-speaker-identification --max-speakers 4
```

## 🔌 API Endpoints

### Core Endpoints

| Endpoint | Method | Description | Port |
|----------|--------|-------------|------|
| `/` | GET | API root, health check | 8000 |
| `/health` | GET | Service health status | 8000 |
| `/docs` | GET | Interactive API documentation (Swagger UI) | 8000 |
| `/redoc` | GET | Alternative API documentation (ReDoc) | 8000 |

### Transcription Endpoints

| Endpoint | Method | Description | Port |
|----------|--------|-------------|------|
| `/transcribe` | POST | Submit audio for transcription | 8000 |
| `/transcriptions` | GET | List all transcriptions | 8000 |
| `/transcriptions/{id}` | GET | Get specific transcription | 8000 |
| `/transcriptions/{id}/export` | GET | Export transcription (TXT/SRT/VTT/JSON/PDF) | 8000 |

### Provider Management

| Endpoint | Method | Description | Port |
|----------|--------|-------------|------|
| `/providers` | GET | List available providers | 8000 |
| `/providers/status` | GET | Check provider availability | 8000 |
| `/estimate-cost` | POST | Estimate transcription cost | 8000 |

### Statistics & History

| Endpoint | Method | Description | Port |
|----------|--------|-------------|------|
| `/stats` | GET | Usage statistics | 8000 |
| `/history` | GET | Transcription history with filters | 8000 |

## 🔧 Provider Configuration

### AWS Transcribe

1. Create AWS account
2. Generate access keys (IAM)
3. Create S3 bucket
4. Grant permissions for Transcribe and S3

```bash
# In .env or export
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_DEFAULT_REGION=eu-central-1
S3_BUCKET_NAME=your-bucket
```

### Azure Speech Services

1. Create Azure account
2. Create Storage Account
3. Enable Cognitive Services - Speech
4. Get keys

```bash
AZURE_STORAGE_ACCOUNT=your_account
AZURE_STORAGE_KEY=your_key
AZURE_SPEECH_KEY=your_speech_key
AZURE_SPEECH_REGION=westeurope
```

### Google Cloud Speech-to-Text

1. Create GCP project
2. Enable Speech-to-Text API
3. Create Service Account
4. Download credentials JSON file

```bash
GCP_PROJECT_ID=your_project
GCP_BUCKET_NAME=your-bucket
GOOGLE_APPLICATION_CREDENTIALS=./gcp-credentials.json
```

## 🛠️ Troubleshooting

### Common Issues and Solutions

#### 1. Docker containers won't start

```bash
# Check if ports are already in use
lsof -i :3000  # Frontend port
lsof -i :8000  # Backend port
lsof -i :5432  # PostgreSQL port

# Solution: Stop conflicting services or change ports in docker-compose
```

#### 2. "Cannot connect to database" error

```bash
# Check database container status
docker compose ps

# View database logs
docker compose logs mongodb  # or postgres for dev mode

# Solution: Ensure database container is healthy
docker compose down -v  # Remove volumes
docker compose up -d mongodb  # Start database first
```

#### 3. Frontend shows "API Connection Failed"

```bash
# Check backend health
curl http://localhost:8000/health

# Check CORS settings in .env
# Ensure CORS_ORIGINS includes http://localhost:3000

# Solution: Restart backend with correct environment
docker compose restart backend
```

#### 4. Cloud provider authentication errors

```bash
# Verify environment variables are loaded
docker compose exec backend env | grep AWS
docker compose exec backend env | grep AZURE
docker compose exec backend env | grep GCP

# Solution: Check .env file has correct credentials
# Restart containers after updating .env
docker compose down
docker compose up
```

#### 5. Hot-reload not working in development

```bash
# For React frontend
# Ensure CHOKIDAR_USEPOLLING=true in docker-compose.dev.yml

# For FastAPI backend
# Check volume mounts in docker-compose.dev.yml
# Should have: - ./src/backend:/app/src/backend:cached

# Solution: Use docker-compose.dev.yml for development
docker compose -f docker-compose.dev.yml up
```

#### 6. Out of memory errors

```bash
# Check Docker resource limits
docker system df
docker stats

# Solution: Increase Docker memory allocation
# Docker Desktop > Preferences > Resources > Memory: 4GB minimum
```

### Logs and Debugging

```bash
# View all logs
docker compose logs -f

# View specific service logs
docker compose logs -f backend
docker compose logs -f frontend

# Access container shell for debugging
docker compose exec backend bash
docker compose exec frontend sh

# Check service health
docker compose ps
curl http://localhost:8000/health
```

## 📊 API Usage Examples

### Using cURL

```bash
# Health check
curl http://localhost:8000/health

# Transcribe audio file
curl -X POST http://localhost:8000/transcribe \
  -F "file=@audio.wav" \
  -F "provider=aws" \
  -F "language=en-US" \
  -F "enable_diarization=true"

# Get transcription history
curl http://localhost:8000/history?limit=10

# Export transcription
curl http://localhost:8000/transcriptions/{id}/export?format=srt
```

### Using Python

```python
import requests

# Upload and transcribe
with open("audio.wav", "rb") as f:
    response = requests.post(
        "http://localhost:8000/transcribe",
        files={"file": f},
        data={
            "provider": "aws",
            "language": "en-US",
            "enable_diarization": True,
            "max_speakers": 4
        }
    )
    
result = response.json()
print(f"Transcription ID: {result['id']}")
print(f"Text: {result['transcript']}")

# Get history
history = requests.get("http://localhost:8000/history").json()
for item in history["items"]:
    print(f"{item['filename']}: {item['provider']} - {item['created_at']}")
```

### Using JavaScript/TypeScript

```javascript
// Upload and transcribe
const formData = new FormData();
formData.append('file', audioFile);
formData.append('provider', 'aws');
formData.append('language', 'en-US');

const response = await fetch('http://localhost:8000/transcribe', {
  method: 'POST',
  body: formData
});

const result = await response.json();
console.log('Transcription:', result.transcript);
```

## 🧪 Testing

### Backend Tests (Python)

```bash
# Run all backend tests
docker compose -f docker-compose.dev.yml run backend pytest

# With coverage
docker compose -f docker-compose.dev.yml run backend pytest --cov=speecher

# Run specific test file
docker compose -f docker-compose.dev.yml run backend pytest tests/test_api.py
```

### Frontend Tests (React/TypeScript)

```bash
# Navigate to frontend directory
cd src/react-frontend

# Run all tests
npm test

# Run tests with coverage
npm test -- --coverage

# Run tests in watch mode
npm test -- --watch
```

### End-to-End Tests

```bash
# Run E2E tests with test profile
docker compose --profile test up test-runner
```

## 🔄 Development Best Practices

### Before Committing Changes

**CRITICAL**: Always verify both tests AND production build locally:

```bash
# 1. Backend: Run tests
cd src/backend
pytest

# 2. Frontend: Run tests
cd src/react-frontend
npm test

# 3. Frontend: Verify production build
npm run build

# 4. Run linters and formatters
npm run lint
npm run format
```

### Why Production Build Verification Matters

- **CI uses production TypeScript settings** which are stricter than development
- **Build-time errors** won't appear in development mode
- **Type checking** is more rigorous in production builds
- **Prevents CI failures** and wasted time

### Recommended Development Workflow

1. **Use development mode** for active coding:
   ```bash
   docker compose -f docker-compose.dev.yml up
   ```

2. **Write tests first** (TDD approach)

3. **Verify changes** with hot-reload

4. **Run test suite** before committing

5. **Build production** to catch any issues

6. **Commit with confidence** knowing CI will pass

## 📈 Performance

| Provider | Processing Time | Accuracy | Cost/min |
|----------|-----------------|----------|----------|
| AWS      | ~30% of audio   | 95-98%   | $0.024   |
| Azure    | ~25% of audio   | 94-97%   | $0.016   |
| GCP      | ~35% of audio   | 93-96%   | $0.018   |

*Approximate data for Polish language

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

### How to Contribute

1. Fork the repository
2. Create branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 📝 License

This project is available under MIT license. See [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- [AWS Transcribe](https://aws.amazon.com/transcribe/)
- [Azure Speech Services](https://azure.microsoft.com/services/cognitive-services/speech-services/)
- [Google Cloud Speech-to-Text](https://cloud.google.com/speech-to-text)
- [FastAPI](https://fastapi.tiangolo.com/)
- [React](https://reactjs.org/)
- [TypeScript](https://www.typescriptlang.org/)
- [MongoDB](https://www.mongodb.com/)
- [PostgreSQL](https://www.postgresql.org/)
- [Docker](https://www.docker.com/)

## 📞 Contact

Project Name: Speecher  
Link: <https://github.com/yourusername/speecher>

---

⭐ If you like this project, leave a star on GitHub!
# Test WireGuard Deployment
# Test WireGuard Deployment - 
test
