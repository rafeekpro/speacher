# Speecher - Docker Setup Guide

## 🚀 Quick Start

### 1. Prepare Configuration

```bash
# Copy example configuration file
cp .env.example .env

# Edit .env file and add cloud access credentials
nano .env
```

### 2. Launch Application

```bash
# Build and run all containers
docker compose up --build

# Or run in background
docker compose up -d --build
```

### 3. Access Application

- **Frontend (Streamlit)**: http://localhost:8501
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **MongoDB**: localhost:27017

## 📋 Requirements

- Docker 20.10+
- Docker Compose 1.29+
- Min. 4GB RAM
- 10GB free disk space

## ⚙️ Cloud Provider Configuration

### AWS
1. Create AWS account and generate access keys
2. Create S3 bucket or use existing one
3. Ensure you have Amazon Transcribe permissions
4. Fill in `.env`:
   ```
   AWS_ACCESS_KEY_ID=your_key
   AWS_SECRET_ACCESS_KEY=your_secret
   AWS_DEFAULT_REGION=eu-central-1
   S3_BUCKET_NAME=your-bucket
   ```

### Azure
1. Create Azure account and Storage Account
2. Enable Azure Speech Services
3. Get access keys
4. Fill in `.env`:
   ```
   AZURE_STORAGE_ACCOUNT=your_account
   AZURE_STORAGE_KEY=your_key
   AZURE_SPEECH_KEY=your_speech_key
   AZURE_SPEECH_REGION=westeurope
   ```

### Google Cloud
1. Create GCP project
2. Enable Speech-to-Text API
3. Download credentials JSON file
4. Place file as `gcp-credentials.json` in root directory
5. Fill in `.env`:
   ```
   GCP_PROJECT_ID=your_project
   GCP_BUCKET_NAME=your-bucket
   GCP_CREDENTIALS_FILE=./gcp-credentials.json
   ```

## 🎨 Application Features

### Frontend - Configuration Panel
- **Cloud provider selection**: AWS, Azure, or GCP
- **Language selection**: 11 languages (PL, EN, DE, ES, FR, IT, PT, RU, ZH, JA)
- **Speaker diarization**: Automatic recognition up to 10 speakers
- **Export formats**: TXT, SRT (subtitles), JSON, VTT, PDF
- **Cost estimation**: Before transcription

### Transcription History
- View all transcriptions
- Filter by name, date, provider
- Preview and download results
- Delete unnecessary records

### API Endpoints
- `POST /transcribe` - New transcription
- `GET /history` - History with filtering
- `GET /transcription/{id}` - Transcription details
- `DELETE /transcription/{id}` - Delete
- `GET /stats` - Usage statistics
- `GET /health` - API status
- `GET /db/health` - MongoDB status

## 🔧 Container Management

```bash
# Stop all containers
docker compose down

# Stop and remove volumes (WARNING: deletes data!)
docker compose down -v

# View logs
docker compose logs -f

# Logs for specific service
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f mongo

# Restart service
docker compose restart backend

# Scale (run multiple backend instances)
docker compose up -d --scale backend=3
```

## 📊 Monitoring

```bash
# Container status
docker compose ps

# Resource usage
docker stats

# Check API health
curl http://localhost:8000/health

# Check MongoDB connection
curl http://localhost:8000/db/health

# View statistics
curl http://localhost:8000/stats
```

## 🐛 Troubleshooting

### Backend cannot connect to MongoDB
```bash
# Check MongoDB logs
docker compose logs mongo

# Restart MongoDB
docker compose restart mongo
```

### Frontend not connecting to backend
```bash
# Check if backend is running
curl http://localhost:8000/health

# Check logs
docker compose logs backend
docker compose logs frontend
```

### Cloud permission errors
- Verify keys in `.env` are correct
- Ensure account has required permissions
- For GCP check if credentials file exists

## 🔒 Security

1. **Never commit `.env` file** - add it to `.gitignore`
2. **Use strong passwords** for MongoDB
3. **Restrict port access** in production
4. **Regularly update** Docker images
5. **Encrypt connections** using reverse proxy (e.g., Nginx)

## 📦 Production Deployment

For production environment:

1. Change default passwords
2. Use Docker Swarm or Kubernetes
3. Add SSL/TLS (e.g., via Traefik)
4. Configure MongoDB backups
5. Monitor logs (e.g., ELK Stack)
6. Set resource limits in docker-compose

```yaml
# Example limits in docker-compose.yml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

## 📝 License

This project is available under MIT license.