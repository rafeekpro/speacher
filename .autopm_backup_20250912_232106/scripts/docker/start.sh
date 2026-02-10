#!/bin/bash
# Start Speecher application in Docker with all services

set -e

echo "Starting Speecher application with Docker Compose..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Docker is not running. Please start Docker first."
    exit 1
fi

# Create necessary directories
mkdir -p docker test_results

# Stop any existing containers
echo "Stopping any existing containers..."
docker compose down 2>/dev/null || true

# Start services
echo "Starting MongoDB, Backend, and Frontend services..."
docker compose up -d

# Wait for services to be healthy
echo "Waiting for services to be healthy..."
max_retries=30
retry_count=0

while [ $retry_count -lt $max_retries ]; do
    if docker compose ps | grep -q "healthy"; then
        echo "Services are healthy!"
        break
    fi
    echo -n "."
    sleep 2
    retry_count=$((retry_count + 1))
done

if [ $retry_count -eq $max_retries ]; then
    echo "Services did not become healthy in time."
    echo "Check logs with: docker compose logs"
    exit 1
fi

echo ""
echo "Speecher is running!"
echo "  - Backend API: http://localhost:8000"
echo "  - Frontend: http://localhost:3000"
echo "  - MongoDB: localhost:27017"
echo ""
echo "To view logs: docker compose logs -f"
echo "To stop: docker compose down"
echo "To run tests: docker compose --profile test up test-runner"