# Multi-stage Dockerfile for FastAPI backend with hot-reload support

# Base stage for Python dependencies
FROM python:3.11-slim AS base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    libpq-dev \
    pkg-config \
    libavformat-dev \
    libavcodec-dev \
    libavdevice-dev \
    libavutil-dev \
    libswscale-dev \
    libswresample-dev \
    libavfilter-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast Python package management
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# Copy dependency files
COPY pyproject.toml uv.lock* README.md ./

# Development stage with hot-reload
FROM base AS development

# Install all dependencies including dev
RUN uv pip install --system -e . --all-extras

# Install additional development tools
RUN uv pip install --system \
    watchfiles \
    ipython \
    ipdb \
    pytest \
    pytest-asyncio \
    pytest-cov \
    httpx

# Copy application code
COPY src/ ./src/
COPY tests/ ./tests/

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command for development with hot-reload
CMD ["uvicorn", "src.backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "/app/src"]

# Production stage (minimal image)
FROM base AS production

# Add uv to PATH
ENV PATH="/root/.local/bin:$PATH"

# Install only production dependencies
RUN uv pip install --system .

# Copy only necessary application code
COPY src/backend/ ./src/backend/
COPY src/speacher/ ./src/speacher/

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Production command without reload
CMD ["uvicorn", "src.backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]