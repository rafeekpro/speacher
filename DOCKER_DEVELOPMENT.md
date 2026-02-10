# Docker Development Guide

This guide explains how to use Docker for development, testing, and production deployment of the Speecher application.

## Overview

The Speecher project uses Docker to ensure consistency across development, CI/CD, and production environments. The setup includes:

- **Backend**: Python FastAPI application
- **Frontend**: React application
- **Databases**: PostgreSQL (primary), MongoDB (legacy), Redis (caching)
- **Development**: Hot-reload enabled for both backend and frontend

## Quick Start

### Prerequisites

- Docker Desktop (version 20.10+)
- Docker Compose (version 2.0+)
- 8GB+ RAM available for Docker
- 10GB+ free disk space

### Development Setup

1. **Clone the repository**:
```bash
git clone https://github.com/yourusername/speecher.git
cd speecher
```

2. **Copy environment variables**:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Start development environment**:
```bash
# Start all services with hot-reload
docker compose -f docker-compose.dev.yml up

# Or run in background
docker compose -f docker-compose.dev.yml up -d

# View logs
docker compose -f docker-compose.dev.yml logs -f backend
docker compose -f docker-compose.dev.yml logs -f frontend
```

4. **Access the application**:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- PostgreSQL: localhost:5432
- MongoDB: localhost:27017
- Redis: localhost:6379

## Docker Files Structure

```
speecher/
├── docker/
│   ├── backend.Dockerfile        # Production backend image
│   ├── react.Dockerfile          # Production frontend image
│   ├── react.dev.Dockerfile      # Development frontend with hot-reload
│   ├── test.Dockerfile           # Test runner image
│   ├── nginx.dev.conf            # Development nginx config
│   ├── nginx.prod.conf           # Production nginx config
│   └── ssl/                      # SSL certificates for HTTPS
├── docker-compose.yml            # Default compose file (production-like)
├── docker-compose.dev.yml        # Development with hot-reload
├── docker-compose.prod.yml       # Production deployment
└── .dockerignore                 # Files to exclude from Docker context
```

## Development Workflow

### Hot-Reload Development

Both backend and frontend support hot-reload in development:

**Backend (FastAPI)**:
- Source code is mounted at `/app/src/backend`
- Changes to Python files trigger automatic reload
- Uvicorn runs with `--reload` flag

**Frontend (React)**:
- Source code is mounted at `/app`
- Webpack dev server detects changes
- Browser auto-refreshes on file changes

### Making Code Changes

1. **Backend changes**:
```bash
# Edit files in src/backend/
# Changes are automatically detected and server reloads
```

2. **Frontend changes**:
```bash
# Edit files in src/react-frontend/
# Browser automatically refreshes
```

3. **Database changes**:
```bash
# Run migrations
docker compose -f docker-compose.dev.yml exec backend alembic upgrade head

# Create new migration
docker compose -f docker-compose.dev.yml exec backend alembic revision --autogenerate -m "description"
```

### Running Tests

```bash
# Run all tests
docker compose -f docker-compose.dev.yml --profile test up test-runner

# Run specific test file
docker compose -f docker-compose.dev.yml run --rm test-runner pytest tests/test_auth.py

# Run with coverage
docker compose -f docker-compose.dev.yml run --rm test-runner pytest --cov=src --cov-report=html

# Run frontend tests
docker compose -f docker-compose.dev.yml exec frontend npm test
```

### Debugging

1. **Backend debugging**:
```bash
# Attach to running container
docker compose -f docker-compose.dev.yml exec backend bash

# View real-time logs
docker compose -f docker-compose.dev.yml logs -f backend

# Python debugger (pdb)
# Add `import pdb; pdb.set_trace()` in your code
```

2. **Frontend debugging**:
```bash
# Attach to running container
docker compose -f docker-compose.dev.yml exec frontend sh

# Use browser DevTools for debugging
# React DevTools extension recommended
```

3. **Database debugging**:
```bash
# PostgreSQL
docker compose -f docker-compose.dev.yml exec postgres psql -U speecher -d speecher_dev

# MongoDB
docker compose -f docker-compose.dev.yml exec mongodb mongosh -u admin -p speecher_admin_pass

# Redis
docker compose -f docker-compose.dev.yml exec redis redis-cli
```

## Building Images

### Development Build

```bash
# Build all services
docker compose -f docker-compose.dev.yml build

# Build specific service
docker compose -f docker-compose.dev.yml build backend
docker compose -f docker-compose.dev.yml build frontend
```

### Production Build

```bash
# Build optimized production images
docker compose -f docker-compose.prod.yml build

# Build with specific version tag
VERSION=1.0.0 docker compose -f docker-compose.prod.yml build

# Push to registry
docker compose -f docker-compose.prod.yml push
```

### Multi-stage Build Optimization

The production Dockerfiles use multi-stage builds to minimize image size:

- **Backend**: ~150MB (Python slim base)
- **Frontend**: ~25MB (nginx alpine base)

## Environment Variables

### Backend Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `REDIS_URL` | Redis connection string | Required |
| `JWT_SECRET_KEY` | JWT signing key | Required |
| `ENVIRONMENT` | Environment name | development |
| `DEBUG` | Enable debug mode | false |
| `LOG_LEVEL` | Logging level | INFO |
| `CORS_ORIGINS` | Allowed CORS origins | http://localhost:3000 |

### Frontend Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `REACT_APP_API_URL` | Backend API URL | http://localhost:8000 |
| `REACT_APP_WS_URL` | WebSocket URL | ws://localhost:8000 |
| `REACT_APP_ENVIRONMENT` | Environment name | development |

## CI/CD Integration

### GitHub Actions

The Docker setup is designed to work seamlessly with GitHub Actions:

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build test image
        run: docker compose -f docker-compose.yml build test-runner
      
      - name: Run tests
        run: docker compose -f docker-compose.yml --profile test up --exit-code-from test-runner test-runner
      
      - name: Build production images
        run: |
          docker compose -f docker-compose.prod.yml build
          
      - name: Security scan
        run: |
          docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
            aquasec/trivy image speecher/backend:latest
```

### Kubernetes Deployment

The same Docker images can be deployed to Kubernetes:

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: speecher-backend
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: backend
        image: speecher/backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: speecher-secrets
              key: database-url
```

## Troubleshooting

### Common Issues

1. **Port already in use**:
```bash
# Find and stop conflicting process
lsof -i :3000
kill -9 <PID>

# Or change port in docker-compose.dev.yml
```

2. **Permission denied errors**:
```bash
# Fix ownership of mounted volumes
docker compose -f docker-compose.dev.yml exec backend chown -R appuser:appuser /app
```

3. **Hot-reload not working**:
```bash
# Ensure CHOKIDAR_USEPOLLING is set for React
# Check that volumes are mounted correctly
docker compose -f docker-compose.dev.yml exec frontend ls -la /app
```

4. **Database connection errors**:
```bash
# Ensure database is healthy
docker compose -f docker-compose.dev.yml ps

# Check database logs
docker compose -f docker-compose.dev.yml logs postgres
```

5. **npm install failures**:
```bash
# Clear npm cache
docker compose -f docker-compose.dev.yml exec frontend npm cache clean --force

# Rebuild without cache
docker compose -f docker-compose.dev.yml build --no-cache frontend
```

### Cleaning Up

```bash
# Stop all containers
docker compose -f docker-compose.dev.yml down

# Remove volumes (WARNING: deletes data)
docker compose -f docker-compose.dev.yml down -v

# Remove all images
docker compose -f docker-compose.dev.yml down --rmi all

# Clean Docker system
docker system prune -a --volumes
```

## Best Practices

1. **Development**:
   - Always use docker-compose.dev.yml for development
   - Mount source code as volumes for hot-reload
   - Use .env files for configuration
   - Commit .env.example with dummy values

2. **Testing**:
   - Run tests in isolated containers
   - Use separate test database
   - Include integration tests with all services

3. **Production**:
   - Never mount source code volumes in production
   - Use specific version tags, not `latest`
   - Implement health checks for all services
   - Set resource limits and reservations

4. **Security**:
   - Run containers as non-root users
   - Use secrets management for sensitive data
   - Regularly update base images
   - Scan images for vulnerabilities

5. **Performance**:
   - Use multi-stage builds to minimize image size
   - Leverage Docker layer caching
   - Use .dockerignore to exclude unnecessary files
   - Optimize Dockerfile instruction order

## Advanced Topics

### Using Docker Buildx for Multi-platform Builds

```bash
# Create buildx builder
docker buildx create --name speecher-builder --use

# Build for multiple platforms
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag speecher/backend:latest \
  --push \
  -f docker/backend.Dockerfile .
```

### Docker Compose Profiles

Use profiles to selectively start services:

```bash
# Start only core services
docker compose -f docker-compose.dev.yml up

# Include nginx proxy
docker compose -f docker-compose.dev.yml --profile with-proxy up

# Include development tools
docker compose -f docker-compose.dev.yml --profile tools up
```

### Volume Performance Optimization

For macOS and Windows, use cached or delegated mounts:

```yaml
volumes:
  - ./src:/app/src:cached      # Host is authoritative
  - ./node_modules:/app/node_modules:delegated  # Container is authoritative
```

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review Docker logs: `docker compose logs <service>`
3. Open an issue on GitHub with:
   - Docker version: `docker --version`
   - Docker Compose version: `docker compose --version`
   - Operating system
   - Error messages and logs