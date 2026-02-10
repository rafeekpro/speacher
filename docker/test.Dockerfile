# Dockerfile for test environment
# Includes both backend and frontend testing capabilities

FROM python:3.11-slim AS test-base

# Set working directory
WORKDIR /app

# Install system dependencies for both Python and Node.js
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    libpq-dev \
    nodejs \
    npm \
    chromium \
    chromium-driver \
    firefox-esr \
    && rm -rf /var/lib/apt/lists/*

# Install uv for Python package management
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# Backend test stage
FROM test-base AS backend-tests

# Copy Python dependency files
COPY pyproject.toml uv.lock* ./

# Install all Python dependencies including test dependencies
RUN uv pip install --system -e . --all-extras

# Install additional testing tools
RUN uv pip install --system \
    pytest \
    pytest-asyncio \
    pytest-cov \
    pytest-xdist \
    pytest-timeout \
    pytest-mock \
    pytest-env \
    httpx \
    faker \
    factory-boy \
    freezegun

# Copy application and test code
COPY src/ ./src/
COPY tests/ ./tests/

# Create directory for test results
RUN mkdir -p /app/test_results /app/coverage

# Set Python path
ENV PYTHONPATH=/app:$PYTHONPATH

# Frontend test stage
FROM test-base AS frontend-tests

# Set working directory for frontend
WORKDIR /app/frontend

# Copy frontend package files
COPY src/react-frontend/package*.json ./

# Install frontend dependencies
RUN npm ci

# Install Playwright browsers
RUN npx playwright install --with-deps chromium firefox

# Copy frontend code
COPY src/react-frontend/ ./

# Create test results directory
RUN mkdir -p /app/test_results /app/coverage

# Combined test stage
FROM test-base AS all-tests

# Copy Python dependencies and install
COPY pyproject.toml uv.lock* ./
RUN uv pip install --system -e . --all-extras

# Install Python test tools
RUN uv pip install --system \
    pytest \
    pytest-asyncio \
    pytest-cov \
    pytest-xdist \
    pytest-timeout \
    pytest-mock \
    pytest-env \
    httpx \
    faker \
    factory-boy \
    freezegun

# Copy backend code
COPY src/ ./src/
COPY tests/ ./tests/

# Setup frontend in subdirectory
WORKDIR /app/frontend
COPY src/react-frontend/package*.json ./
RUN npm ci

# Install Playwright
RUN npx playwright install --with-deps chromium firefox

# Copy frontend code
COPY src/react-frontend/ ./

# Back to app root
WORKDIR /app

# Create test results directories
RUN mkdir -p /app/test_results /app/coverage /app/playwright-report

# Create test runner script
RUN cat > /app/run_tests.sh << 'EOF'
#!/bin/bash
set -e

echo "Starting test suite..."

# Parse command line arguments
TEST_TYPE="${1:-all}"

case "$TEST_TYPE" in
    backend)
        echo "Running backend tests..."
        pytest tests/ \
            -v \
            --tb=short \
            --cov=src \
            --cov-report=html:/app/coverage/backend \
            --cov-report=xml:/app/test_results/backend-coverage.xml \
            --junit-xml=/app/test_results/backend-results.xml
        ;;
    
    frontend)
        echo "Running frontend tests..."
        cd /app/frontend
        npm test -- --coverage --watchAll=false
        cp -r coverage/* /app/coverage/frontend/ 2>/dev/null || true
        ;;
    
    e2e)
        echo "Running E2E tests..."
        cd /app/frontend
        npx playwright test
        cp -r playwright-report/* /app/playwright-report/ 2>/dev/null || true
        ;;
    
    all)
        echo "Running all tests..."
        
        # Backend tests
        echo "=== Backend Tests ==="
        pytest tests/ \
            -v \
            --tb=short \
            --cov=src \
            --cov-report=html:/app/coverage/backend \
            --cov-report=xml:/app/test_results/backend-coverage.xml \
            --junit-xml=/app/test_results/backend-results.xml || true
        
        # Frontend unit tests
        echo "=== Frontend Tests ==="
        cd /app/frontend
        npm test -- --coverage --watchAll=false || true
        cp -r coverage/* /app/coverage/frontend/ 2>/dev/null || true
        
        # E2E tests
        echo "=== E2E Tests ==="
        npx playwright test || true
        cp -r playwright-report/* /app/playwright-report/ 2>/dev/null || true
        ;;
    
    *)
        echo "Unknown test type: $TEST_TYPE"
        echo "Usage: $0 [backend|frontend|e2e|all]"
        exit 1
        ;;
esac

echo "Test suite completed!"
EOF

# Make script executable
RUN chmod +x /app/run_tests.sh

# Set environment variables
ENV PYTHONPATH=/app:$PYTHONPATH
ENV NODE_ENV=test

# Create non-root user
RUN useradd -m -u 1000 testuser && \
    chown -R testuser:testuser /app

# Switch to non-root user
USER testuser

# Default command runs all tests
CMD ["/app/run_tests.sh", "all"]