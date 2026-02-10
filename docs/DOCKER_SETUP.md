# Speecher Docker Setup

## Overview
Speecher is configured to run entirely in Docker with automatic MongoDB setup, hot-reload for development, and comprehensive testing.

## Architecture
- **MongoDB**: Database with automatic initialization
- **Backend**: FastAPI with hot-reload (port 8000)
- **Frontend**: Streamlit with hot-reload (port 8501)
- **Test Runner**: Pytest integration tests

## Quick Start

### 1. Start the Application
```bash
./docker-start.sh
```
This will:
- Start MongoDB with initial database setup
- Start Backend API with hot-reload
- Start Frontend UI
- Wait for all services to be healthy

### 2. Access the Application
- Frontend: http://localhost:8501
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- MongoDB: localhost:27017

### 3. Stop the Application
```bash
./docker-stop.sh
```

## Development Features

### Hot-Reload
All source code is mounted as volumes, so changes are reflected immediately:
- Backend: Any changes to `src/backend/` or `src/speecher/` 
- Frontend: Any changes to `src/frontend/`

### API Key Configuration
1. Open the frontend at http://localhost:8501
2. Go to Settings → API Keys
3. Configure your cloud provider credentials

Or use the API directly:
```bash
curl -X POST http://localhost:8000/api/keys/aws \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "aws",
    "keys": {
      "access_key_id": "your_key",
      "secret_access_key": "your_secret",
      "region": "us-east-1",
      "s3_bucket_name": "your-bucket"
    }
  }'
```

## Testing

### Run Integration Tests
```bash
./docker-test.sh
```

### Run Tests Manually
```bash
docker compose --profile test up test-runner
```

### Test Results
Test results are saved to `test_results/results.xml`

## Docker Commands

### View Logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend
docker compose logs -f mongodb
```

### Restart a Service
```bash
docker compose restart backend
```

### Execute Commands in Container
```bash
# Backend shell
docker compose exec backend bash

# MongoDB shell
docker compose exec mongodb mongosh -u admin -p speecher_admin_pass
```

### Clean Everything
```bash
# Stop and remove containers
docker compose down

# Also remove data volumes
docker compose down -v
```

## Environment Variables

Copy `.env.example` to `.env` if you want to set environment variables:
```bash
cp .env.example .env
```

Most configuration can be done through the UI, but you can set:
- AWS credentials
- Azure credentials
- GCP credentials
- MongoDB settings (handled automatically by Docker)

## Database

MongoDB is automatically initialized with:
- Database: `speecher`
- User: `speecher_user`
- Password: `speecher_pass`
- Collections: `transcriptions`, `api_keys`
- Test database: `speecher_test`

### Access MongoDB
```bash
# Using mongosh
docker compose exec mongodb mongosh -u speecher_user -p speecher_pass speecher

# Show collections
> show collections

# Query transcriptions
> db.transcriptions.find().pretty()
```

## Troubleshooting

### Services Not Starting
```bash
# Check status
docker compose ps

# Check logs
docker compose logs mongodb
docker compose logs backend
```

### Port Already in Use
If ports 8000, 8501, or 27017 are already in use:
```bash
# Find process using port
lsof -i :8000

# Or change ports in docker-compose.yml
```

### MongoDB Connection Issues
```bash
# Check MongoDB is running
docker compose ps mongodb

# Check MongoDB logs
docker compose logs mongodb

# Test connection
docker compose exec mongodb mongosh -u admin -p speecher_admin_pass --eval "db.runCommand({ping: 1})"
```

### Clean Start
```bash
# Remove everything and start fresh
docker compose down -v
docker system prune -f
./docker-start.sh
```

## Performance

The setup includes:
- Health checks for all services
- Automatic restart on failure
- Volume mounts for hot-reload
- Optimized Docker layers for fast rebuilds

## Security Notes

- API keys are encrypted in the database
- MongoDB requires authentication
- Services communicate over internal Docker network
- Sensitive values are masked in API responses

## Development Workflow

1. Start services: `./docker-start.sh`
2. Make code changes (hot-reload will apply them)
3. Run tests: `./docker-test.sh`
4. View logs: `docker compose logs -f backend`
5. Stop when done: `./docker-stop.sh`

## Advanced Usage

### Run with Custom Environment
```bash
docker compose --env-file .env.production up
```

### Scale Services
```bash
docker compose up --scale backend=3
```

### Build Images
```bash
docker compose build --no-cache
```

### Export/Import Database
```bash
# Export
docker compose exec mongodb mongodump -u admin -p speecher_admin_pass --out /tmp/backup
docker cp speecher-mongodb:/tmp/backup ./backup

# Import
docker cp ./backup speecher-mongodb:/tmp/backup
docker compose exec mongodb mongorestore -u admin -p speecher_admin_pass /tmp/backup
```