#!/bin/bash
# Stop and clean up Speecher Docker containers

set -e

echo "Stopping Speecher services..."

# Stop all services
docker compose down

# Optional: Remove volumes (uncomment if you want to clear data)
# docker compose down -v

echo "Speecher services stopped."
echo ""
echo "To completely remove all data and volumes, run:"
echo "  docker compose down -v"