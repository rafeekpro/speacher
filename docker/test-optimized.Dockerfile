# syntax=docker/dockerfile:1.5
# Optimized Test Container with Multi-stage Build
# Supports Python 3.11 backend tests with pytest
# Features: dependency caching, bytecode compilation, security hardening

ARG PYTHON_VERSION=3.11
ARG UV_VERSION=0.5.15

# ============================================
# Stage 1: Dependency Builder
# ============================================
FROM python:${PYTHON_VERSION}-slim AS dependencies

# Build arguments for caching
ARG UV_VERSION
ARG BUILDKIT_INLINE_CACHE=1

# Install build dependencies
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast Python dependency management
RUN curl -LsSf https://astral.sh/uv/${UV_VERSION}/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

WORKDIR /app

# Copy dependency files only (for better layer caching)
COPY pyproject.toml uv.lock* ./

# Install dependencies with caching
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    uv pip install --system --compile-bytecode \
    -e . --all-extras

# Install test dependencies explicitly
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    uv pip install --system --compile-bytecode \
    pytest==7.4.3 \
    pytest-cov==4.1.0 \
    pytest-asyncio==0.21.1 \
    pytest-xdist==3.5.0 \
    pytest-timeout==2.2.0 \
    pytest-mock==3.12.0 \
    pytest-env==1.1.3 \
    mongomock==4.1.2 \
    httpx==0.25.1 \
    faker==20.1.0 \
    factory-boy==3.3.0 \
    freezegun==1.2.2

# Pre-compile Python bytecode for faster startup
RUN python -m compileall -b /usr/local/lib/python${PYTHON_VERSION}/site-packages

# ============================================
# Stage 2: Source Builder
# ============================================
FROM dependencies AS source

WORKDIR /app

# Copy source code
COPY src/ ./src/
COPY tests/ ./tests/

# Pre-compile application bytecode
RUN python -m compileall -b src/ tests/

# Create test artifacts directories
RUN mkdir -p /app/test_results /app/coverage /app/.pytest_cache

# ============================================
# Stage 3: Runtime Image
# ============================================
FROM python:${PYTHON_VERSION}-slim AS runtime

# Metadata labels
LABEL maintainer="rafal.lagowski@accenture.com" \
      version="1.0.0" \
      description="Optimized test container for Speecher project" \
      org.opencontainers.image.source="https://github.com/speecher/speecher" \
      org.opencontainers.image.vendor="Accenture" \
      org.opencontainers.image.licenses="MIT"

# Install runtime dependencies only
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user with specific UID/GID for consistency
RUN groupadd -g 1000 testuser && \
    useradd -m -u 1000 -g testuser testuser

WORKDIR /app

# Copy Python packages from dependencies stage
COPY --from=dependencies --chown=testuser:testuser \
    /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copy pre-compiled application code
COPY --from=source --chown=testuser:testuser /app ./

# Create health check script
RUN cat > /app/healthcheck.py << 'EOF'
#!/usr/bin/env python3
"""Health check script for test container."""
import sys
import subprocess

def check_pytest():
    """Check if pytest is available and functional."""
    try:
        result = subprocess.run(
            ["python", "-c", "import pytest; print(pytest.__version__)"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False

def check_dependencies():
    """Check if core dependencies are importable."""
    try:
        import fastapi
        import pydantic
        import httpx
        import pytest
        import pytest_asyncio
        return True
    except ImportError:
        return False

def main():
    """Run health checks."""
    checks = {
        "pytest": check_pytest(),
        "dependencies": check_dependencies(),
    }
    
    if all(checks.values()):
        print("Health check passed")
        sys.exit(0)
    else:
        failed = [k for k, v in checks.items() if not v]
        print(f"Health check failed: {', '.join(failed)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
EOF

# Make health check executable
RUN chmod +x /app/healthcheck.py && \
    chown testuser:testuser /app/healthcheck.py

# Create optimized test runner script
RUN cat > /app/run_tests.sh << 'EOF'
#!/bin/bash
set -euo pipefail

# Test runner with optimizations
echo "Starting optimized test suite..."

# Environment setup
export PYTHONPATH=/app:${PYTHONPATH:-}
export PYTEST_CACHE_DIR=/app/.pytest_cache
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1

# Parse arguments
TEST_TYPE="${1:-unit}"
PARALLEL="${2:-auto}"
VERBOSE="${3:-}"

# Configure pytest options
PYTEST_BASE_OPTS="-v --tb=short --strict-markers"
PYTEST_COV_OPTS="--cov=src --cov-report=term-missing --cov-report=html:/app/coverage --cov-report=xml:/app/test_results/coverage.xml"
PYTEST_OUTPUT_OPTS="--junit-xml=/app/test_results/junit.xml"

# Add parallel execution if requested
if [ "$PARALLEL" != "no" ]; then
    PYTEST_BASE_OPTS="$PYTEST_BASE_OPTS -n $PARALLEL"
fi

# Add verbose output if requested
if [ "$VERBOSE" = "verbose" ] || [ "$VERBOSE" = "-v" ]; then
    PYTEST_BASE_OPTS="$PYTEST_BASE_OPTS -vv"
fi

# Execute tests based on type
case "$TEST_TYPE" in
    unit)
        echo "Running unit tests..."
        pytest tests/unit/ $PYTEST_BASE_OPTS $PYTEST_COV_OPTS $PYTEST_OUTPUT_OPTS
        ;;
    
    integration)
        echo "Running integration tests..."
        pytest tests/integration/ $PYTEST_BASE_OPTS $PYTEST_COV_OPTS $PYTEST_OUTPUT_OPTS
        ;;
    
    all)
        echo "Running all tests..."
        pytest tests/ $PYTEST_BASE_OPTS $PYTEST_COV_OPTS $PYTEST_OUTPUT_OPTS
        ;;
    
    smoke)
        echo "Running smoke tests..."
        pytest tests/ -m smoke $PYTEST_BASE_OPTS --maxfail=1
        ;;
    
    coverage)
        echo "Running tests with coverage focus..."
        pytest tests/ $PYTEST_BASE_OPTS $PYTEST_COV_OPTS $PYTEST_OUTPUT_OPTS --cov-fail-under=80
        ;;
    
    *)
        echo "Unknown test type: $TEST_TYPE"
        echo "Usage: $0 [unit|integration|all|smoke|coverage] [parallel:auto|no|N] [verbose]"
        exit 1
        ;;
esac

echo "Test suite completed!"

# Output coverage summary
if [ -f /app/test_results/coverage.xml ]; then
    echo "Coverage report available at /app/coverage/index.html"
    python -c "
import xml.etree.ElementTree as ET
tree = ET.parse('/app/test_results/coverage.xml')
root = tree.getroot()
coverage = float(root.attrib.get('line-rate', 0)) * 100
print(f'Overall coverage: {coverage:.2f}%')
"
fi
EOF

# Make test runner executable
RUN chmod +x /app/run_tests.sh && \
    chown testuser:testuser /app/run_tests.sh

# Set environment variables
ENV PYTHONPATH=/app:$PYTHONPATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTEST_CACHE_DIR=/app/.pytest_cache \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Configure pytest settings
RUN cat > /app/pytest.ini << 'EOF'
[pytest]
testpaths = tests
python_files = test_*.py *_test.py
python_classes = Test*
python_functions = test_*
addopts = 
    --strict-markers
    --strict-config
    --verbose
    --tb=short
    --disable-warnings
markers =
    smoke: Smoke tests for quick validation
    slow: Tests that take > 1 second
    integration: Integration tests requiring external services
    unit: Unit tests (default)
asyncio_mode = auto
timeout = 300
timeout_method = thread
EOF

RUN chown testuser:testuser /app/pytest.ini

# Switch to non-root user
USER testuser

# Health check configuration
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python /app/healthcheck.py || exit 1

# Set working directory
WORKDIR /app

# Default entrypoint for pytest with optimizations
ENTRYPOINT ["python", "-m", "pytest"]

# Default command runs unit tests
CMD ["tests/unit/", "-v", "--tb=short"]

# ============================================
# Stage 4: CI/CD Optimized Image (optional)
# ============================================
FROM runtime AS ci

# Additional CI/CD tools
USER root
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    git \
    make \
    && rm -rf /var/lib/apt/lists/*

# Install code quality tools
RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    pip install --no-cache-dir \
    black==23.11.0 \
    ruff==0.1.0 \
    mypy==1.7.0 \
    bandit==1.7.5 \
    safety==3.0.0

# Create CI runner script
RUN cat > /app/run_ci.sh << 'EOF'
#!/bin/bash
set -euo pipefail

echo "Running CI pipeline..."

# Code formatting check
echo "Checking code formatting..."
black --check src/ tests/

# Linting
echo "Running linter..."
ruff check src/ tests/

# Type checking
echo "Running type checker..."
mypy src/ --ignore-missing-imports

# Security scanning
echo "Running security scan..."
bandit -r src/ -f json -o /app/test_results/bandit.json || true
safety check --json > /app/test_results/safety.json || true

# Run tests with coverage
echo "Running tests..."
/app/run_tests.sh all auto

echo "CI pipeline completed!"
EOF

RUN chmod +x /app/run_ci.sh && \
    chown testuser:testuser /app/run_ci.sh

USER testuser

# Override entrypoint for CI
ENTRYPOINT ["/app/run_ci.sh"]

# ============================================
# Build Cache Mount Points for CI/CD
# ============================================
# When building, use these cache mounts for faster builds:
# --mount=type=cache,target=/root/.cache/uv
# --mount=type=cache,target=/root/.cache/pip
# --mount=type=cache,target=/var/cache/apt
# --mount=type=cache,target=/var/lib/apt

# ============================================
# Usage Examples
# ============================================
# Build the optimized test image:
# docker build -f docker/test-optimized.Dockerfile --target runtime -t speecher-test:latest .
#
# Build CI/CD variant:
# docker build -f docker/test-optimized.Dockerfile --target ci -t speecher-test:ci .
#
# Run unit tests:
# docker run --rm speecher-test:latest tests/unit/
#
# Run all tests with coverage:
# docker run --rm -v ./test_results:/app/test_results speecher-test:latest tests/ --cov=src
#
# Run with custom script:
# docker run --rm --entrypoint /app/run_tests.sh speecher-test:latest all
#
# Run CI pipeline:
# docker run --rm -v ./test_results:/app/test_results speecher-test:ci
#
# Interactive debugging:
# docker run -it --rm --entrypoint /bin/bash speecher-test:latest
#
# With BuildKit cache mounts (faster rebuilds):
# DOCKER_BUILDKIT=1 docker build \
#   --cache-from speecher-test:latest \
#   --build-arg BUILDKIT_INLINE_CACHE=1 \
#   -f docker/test-optimized.Dockerfile \
#   -t speecher-test:latest .